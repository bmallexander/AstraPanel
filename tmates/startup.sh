arch=$(uname -m)
real_arch=""
case $arch in
    x86_64*) real_arch="amd64" ;;
    armv6l*) real_arch="arm32v6" ;;
    armv7l*) real_arch="arm32v7" ;;
    aarch64*) real_arch="arm64v8" ;;
    i686*) real_arch="i386" ;;
    *) real_arch="unknown" ;;
esac
base_path="/mnt/tmates/tmate-2.4.0-static-linux-"
tmate_path="${base_path}${real_arch}/tmate"
execute="$tmate_path $@"
echo $execute
$execute