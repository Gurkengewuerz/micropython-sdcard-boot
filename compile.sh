#!/bin/bash

git_hash=$(git log --pretty=format:'%h' -n 1)
git_branch=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)

working_dir=$(pwd)

echo "run compilation for $git_branch ($git_hash)"

echo "generate working directories"
mkdir -p build/
mkdir -p output/


echo "copy non python files to build directory"
for file in $(find src/ -type f ! -name '*.py' ! -name 'compile.exclude')
do
    NEWFILE="build/$(echo "$file" | cut -d'/' -f2-)"
    mkdir -p $(dirname "$NEWFILE")
    cp -f "$file" "$NEWFILE"
done    


echo "copy excluded python files"
for file in $(printf "%s\n" $(grep -v '^#' src/compile.exclude) | grep -P .*.py)
do
    OUTPUT="build/$(echo $file | cut -d'/' -f2-)"
    mkdir -p $(dirname "$OUTPUT")
    cp -f "$file" "$OUTPUT"
done


echo "compiling non excluded python files"
for file in $(find src/ -name '*.py' $(printf "! -wholename %s " $(grep -v '^#' src/compile.exclude)))
do
    OUTPUT="build/$(echo $file | cut -d'/' -f2- | cut -d. -f1).mpy"
    mkdir -p $(dirname "$OUTPUT")
    mpy-cross $file -o "$OUTPUT"
done


echo "building opt package"
cd build/ && tar -cf ../output/${git_branch}-${git_hash}.tar *
cd "$working_dir"

echo "generating opt package hash"
sha1sum output/*.tar | cut -d ' ' -f 1 > output/hash

echo "generating version line"
echo "0.0.0;$(ls output/*.tar);$(cat output/hash)" > output/versions

cat output/versions

echo "delete build directory"
rm -rf build/