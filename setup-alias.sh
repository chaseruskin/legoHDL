#!/bin/zsh
program="legoHDL"

shell=$(basename "$SHELL")
echo $(pwd)
base=$(dirname "$0")
config_file=~/.$shell"rc"

path=$(pwd)'/'$base'/manager.py'
echo 'PATH' $path
pathToProgram=$path $*
cd ~; echo "alias "$program"="\""python3" \'$path\' '$*'\" >> $config_file

echo "\nSuccessfully placed an alias called "\"$program\"" into your "$config_file
echo "Try it out by opening a new terminal and typing "\"$program" help\""
