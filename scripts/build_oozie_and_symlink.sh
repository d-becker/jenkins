#!/bin/bash

function replace_symlink_if_exists {
# Simply using ln -sfT failed from within Jenkins for some reason...
    local source=$1
    local target=$2

    if [ -L "$target" ]; then
	rm "$target"
    fi

    ln -s "$source" "$target"
}

function symlink_reference_found {
    local filenames=( "$@" )
    local paths=( "${filenames[@]/#/configurations/}" )
    echo "Configuration filenames: " && echo "${paths[@]}".
    
    grep -q "symlink_to_oozie_distro" "${paths[@]}"
}

args=( "$@" )
oozie_branch="${args[0]}"
configuration_files=( "${args[@]:1}" )
if [ ! -L test_symlink_to_oozie_distro ]; then
    if symlink_reference_found "${configuration_files[@]}"; then
	cd testing && \
	git clone https://github.com/apache/oozie.git && \
	cd oozie && \
	git checkout "$oozie_branch" && \
	echo "Cwd: $(pwd)" && \
        bin/mkdistro.sh -Puber -Ptez -DskipTests && \
        REL_PATH=$(find . -regex "./distro/target/oozie-.*-distro/oozie-[^/]*") && \
        echo "Relative path: ${REL_PATH}" && \
        replace_symlink_if_exists "$(pwd)/${REL_PATH}" ../../symlink_to_oozie_distro
    else
	echo "No reference to symlink_to_oozie_distro in BuildConfiguration files, not building custom Oozie."
    fi
else
	replace_symlink_if_exists test_symlink_to_oozie_distro symlink_to_oozie_distro;
fi
