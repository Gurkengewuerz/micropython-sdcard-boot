import gc
import os
import uerrno
import uhashlib
import ubinascii

from . import urequests
from . import utarfile


class OTA:

    def __init__(self, url, main_dir="app", new_version_dir="next", headers={}, quite=True, force_update=False):
        self.url = url.rstrip("/")
        self.new_version_dir = new_version_dir.rstrip("/")
        self.main_dir = main_dir.rstrip("/")
        self.headers = headers
        self.tar_name = "firmware.tar"
        self.quite = quite
        self.force_update = force_update

        if "User-Agent" not in headers:
            self.headers["User-Agent"] = "mc8051 OTAUpdater/1.0.0"

    def install_update_if_available(self) -> bool:
        """This method will immediately install the latest version if out-of-date.
        
        This method expects an active internet connection and allows you to decide yourself
        if you want to install the latest version. It is necessary to run it directly after boot 
        (for memory reasons) and you need to restart the microcontroller if a new version is found.

        Returns
        -------
            bool: true if a new version is available, false otherwise
        """

        current_version, latest_version, remote_filename, remote_hash = self._check_for_new_version()
        if latest_version > current_version or self.force_update:
            not self.quite and print("Updating to version {}...".format(latest_version))
            try:
                self._delete_failed()
                self._create_new_version_file(latest_version)
                self._download_new_version(latest_version, remote_filename, remote_hash)
                self._unpack_tar() # start to get critical here
                self._delete_old_version()
                self._install_new_version()
            except Exception as e:
                not self.quite and print("Failed to update")
                self._delete_failed()
                raise e
            return True
        gc.collect()
        return False

    def _check_for_new_version(self):
        current_version = self.get_version(self.main_dir)
        latest_version, remote_filename, remote_hash = self.get_latest_version()

        not self.quite and print("Checking version... ")
        not self.quite and print("\tCurrent version: ", current_version)
        not self.quite and print("\tLatest version: ", latest_version)
        return current_version, latest_version, remote_filename, remote_hash

    def _create_new_version_file(self, latest_version):
        self.mkdir(self.new_version_dir)
        with open(self.new_version_dir + "/.version", "w") as versionfile:
            versionfile.write(latest_version)
            versionfile.close()

    def get_version(self, directory, version_file_name=".version"):
        if version_file_name in os.listdir(directory):
            with open(directory + "/" + version_file_name) as f:
                version = f.read()
                return version
        return "0.0.0"

    def get_latest_version(self):
        response = urequests.get(self.url + "/versions", headers=self.headers)
        try:
            versions = response.text.strip().split("\n")
            remote_version, remote_filename, remote_hash = versions[-1].strip().rstrip(";").split(";")
            return remote_version, remote_filename, remote_hash
        except:
            return "0.0.0", "", ""
        finally:
            gc.collect()

    def _download_new_version(self, version, remote_filename, remote_hash):
        not self.quite and print("Downloading version {}".format(version))
        
        self._rm_if_exists(self.tar_name)

        if remote_hash:
            hash_obj = uhashlib.sha1()
        
        response = urequests.get(self.url + "/" + remote_filename)
        written_bytes = 0
        with open(self.tar_name, "wb") as f:
            while True:
                chunk = response.raw.read(512)
                if not chunk:
                    break
                if remote_hash:
                    hash_obj.update(chunk)
                written_bytes += f.write(chunk)
        gc.collect()
        not self.quite and print("{} saved ({} bytes)".format(self.tar_name, written_bytes))
        if not self._exists_file(self.tar_name):
            not self.quite and print("Failed to download version {} to {}".format(version, self.tar_name))
            raise AssertionError("file not found")

        if remote_hash and ubinascii.hexlify(hash_obj.digest()).decode().lower() != remote_hash.lower():
            not self.quite and print("Version {} hash does not match remote hash".format(version))
            self._rm_if_exists(self.tar_name)
            raise AssertionError("invalid hash")

        not self.quite and print("Version {} downloaded {}".format(version, self.tar_name))
    
    def _unpack_tar(self):
        not self.quite and print("Unpacking new version")
        with open(self.tar_name, "rb") as f:
            f = utarfile.TarFile(fileobj=f)
            for _file in f:
                file_name = _file.name
                file_name = file_name.replace(self.main_dir + "/", self.new_version_dir + "/")
                if file_name.endswith("/"):  # is a directory
                    self._mk_dirs(file_name[:-1]) # without trailing slash or fail with errno 22
                    continue
                
                hash_obj = None
                orig_hash = ""
                if not self.new_version_dir in file_name and self._exists_file(file_name):
                    hash_obj = uhashlib.sha1()
                    with open(file_name, "rb") as orig:
                        while True:
                            chunk = orig.read(512)
                            if not chunk:
                                break
                            hash_obj.update(chunk)
                    orig_hash = ubinascii.hexlify(hash_obj.digest()).decode()
                    hash_obj = uhashlib.sha1() # create a new hash_obj for new use

                tmp_filename = file_name
                if hash_obj is not None:
                    tmp_filename += ".ota"
                file_obj = f.extractfile(_file)
                with open(tmp_filename, "wb") as f_out:
                    written_bytes = 0
                    while True:
                        buf = file_obj.read(512)
                        if not buf:
                            break
                        if hash_obj is not None:
                            hash_obj.update(buf)
                        written_bytes += f_out.write(buf)
                not self.quite and print("Unpacked {}".format(tmp_filename))
                if hash_obj is not None:
                    new_hash = ubinascii.hexlify(hash_obj.digest()).decode()
                    if new_hash == orig_hash: # is same - do not risk a replace (can currupt file)
                        self._rm_if_exists(tmp_filename)
                        not self.quite and print("Removed {} - file is still the same".format(tmp_filename))
                    else: # is not same - we must replace the old file
                        self._rm_if_exists(file_name)
                        os.rename(tmp_filename, file_name)

        self._rm_if_exists(self.tar_name)
        gc.collect()
        not self.quite and print("Unpacked new version")

    def _delete_old_version(self):
        not self.quite and print("Deleting old version at {} ...".format(self.main_dir))
        self._rmtree(self.main_dir)
        not self.quite and print("Deleted old version at {} ...".format(self.main_dir))

    def _install_new_version(self):
        not self.quite and print("Installing new version at {} ...".format(self.main_dir))
        if self._os_supports_rename():
            os.rename(self.new_version_dir, self.main_dir)
        else:
            self._copy_directory(self.new_version_dir, self.main_dir)
            self._rmtree(self.new_version_dir)
        not self.quite and print("Update installed, please reboot now")

    def _delete_failed(self):
        not self.quite and print("Deleting failed update {} ...".format(self.new_version_dir))
        self._rmtree(self.new_version_dir)
        not self.quite and print("Deleted failed version at {} ...".format(self.new_version_dir))

    def _rmtree(self, directory):
        try:
            for entry in os.ilistdir(directory):
                is_dir = entry[1] == 0x4000
                if is_dir:
                    self._rmtree(directory + "/" + entry[0])
                else:
                    os.remove(directory + "/" + entry[0])
            os.rmdir(directory)
        except OSError as e:
            if e.errno == uerrno.ENOENT: 
                pass
            else:
                raise e

    def _rm_if_exists(self, file):
        try:
            os.remove(file)
        except OSError as e:
            if e.errno == uerrno.ENOENT: 
                pass
            else:
                raise e

    def _os_supports_rename(self) -> bool:
        self._mk_dirs("otaUpdater/osRenameTest")
        os.rename("otaUpdater", "otaUpdated")
        result = len(os.listdir("otaUpdated")) > 0
        self._rmtree("otaUpdated")
        return result

    def _copy_directory(self, fromPath, toPath):
        if not self._exists_dir(toPath):
            self._mk_dirs(toPath)

        for entry in os.ilistdir(fromPath):
            is_dir = entry[1] == 0x4000
            if is_dir:
                self._copy_directory(fromPath + "/" + entry[0], toPath + "/" + entry[0])
            else:
                self._copy_file(fromPath + "/" + entry[0], toPath + "/" + entry[0])

    def _copy_file(self, fromPath, toPath):
        with open(fromPath) as fromFile:
            with open(toPath, "w") as toFile:
                CHUNK_SIZE = 512 # bytes
                data = fromFile.read(CHUNK_SIZE)
                while data:
                    toFile.write(data)
                    data = fromFile.read(CHUNK_SIZE)
            toFile.close()
        fromFile.close()

    def _exists_dir(self, path) -> bool:
        try:
            os.listdir(path)
            return True
        except:
            return False

    def _exists_file(self, path) -> bool:
        try:
            os.stat(path)
            return True
        except:
            return False

    def _mk_dirs(self, path:str):
        paths = path.split("/")

        pathToCreate = ""
        for x in paths:
            self.mkdir(pathToCreate + x)
            pathToCreate = pathToCreate + x + "/"

    # different micropython versions act differently when directory already exists
    def mkdir(self, path:str):
        try:
            os.mkdir(path)
        except OSError as e:
            if e.errno == uerrno.EEXIST: 
                pass
            else:
                raise e
