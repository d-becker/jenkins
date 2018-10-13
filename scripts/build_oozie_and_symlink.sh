#!/bin/bash -xv

function replace_symlink_if_exists {
# Simply using ln -sfT failed from within Jenkins for some reason...
    local source=$1
    local target=$2

    if [ -L "$target" ]; then
	rm "$target"
    fi

    ln -s "$source" "$target"
}

if [ ! -L test_symlink_to_oozie_distro ]; then 
	cd testing/oozie \
	&& echo "Cwd: $(pwd)" \
       	&& bin/mkdistro.sh -Puber -Ptez -DskipTests \
       	&& REL_PATH=$(find . -regex "./distro/target/oozie-.*-distro/oozie-[^/]*") \
	&& echo "Relative path: ${REL_PATH}" \
	&& replace_symlink_if_exists "$(pwd)/${REL_PATH}" ../../symlink_to_oozie_distro; \
else
	replace_symlink_if_exists test_symlink_to_oozie_distro symlink_to_oozie_distro;
fi
