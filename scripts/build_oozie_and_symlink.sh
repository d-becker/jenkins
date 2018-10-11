#!/bin/bash
if [ ! -L test_symlink_to_oozie_distro ]; then 
	cd testing/oozie \
	&& echo "Cwd: $(pwd)" \
       	&& bin/mkdistro.sh -Puber -Ptez -DskipTests \
       	&& REL_PATH=$(find . -regex "./distro/target/oozie-.*-distro/oozie-[^/]*") \
	&& echo "Relative path: ${REL_PATH}" \
	&& ln -sf "$(pwd)/${REL_PATH}" ../../symlink_to_oozie_distro; \
else 
	ln -sf test_symlink_to_oozie_distro symlink_to_oozie_distro;
fi
