#!/bin/sh
originDir=$(pwd)
touch checksum.conf checksum.log
. ./checksum.conf
if [ "${StopT+x}" ] ;then StartT=${StopT} ;else StartT="2000-01-01 00:01" ;fi
export StopT=$(date '+%Y-%m-%d %H:%M')
export StopTymd=$(date '+%Y-%m-%d')
echo "StartT=\"${StartT}\"" > checksum.conf
echo "StopT=\"${StopT}\"" >> checksum.conf
# file folder, should point filestore or filestore/33
export baseDataDir=/opt/jfrog/artifactory/var/data/artifactory/filestore
# lines of per file
export perfilelines=10
# thread of checksum
export thread_num=4

# mkdir a date folder for save the checksum log
mkdir -p "/opt/${StopTymd}" && cd "/opt/${StopTymd}"
# find 2000-01-01 to now file, save to the data.filelist
echo -en "Finding artifacts from ${StartT} to ${StopT}" >> ${originDir}/checksum.log
echo -e " **** $(date '+%Y-%m-%d %H:%M:%S') - Finding artifacts **** "
find ${baseDataDir} -not \( -path ./_pre -prune \) -type f \( -newermt "$StartT"  -not -newermt "$StopT" \) |gawk -F/ '/[a-fA-F0-9]{40}$/{print $NF,$0}' > ${StopTymd}.filelist
# all the artifacts count
totalcount=$(cat ${StopTymd}.filelist|wc -l)

# split the large file
if [ -s "${StopTymd}.filelist" ]; then
  split -l ${perfilelines} ${StopTymd}.filelist -d -a 4 ${StopTymd}.filelist_
else
  echo " **** Empty artifact list, exit script **** "
  echo -e "| Empty artifact list, exit script" >>${originDir}/checksum.log
  exit 1
fi
# files count
wc=$(ls ${StopTymd}.filelist_*|grep -v '.sha1'|wc -l)
# print split files count and total artifacts count
echo -en "| $(date '+%Y-%m-%d %H:%M') - Artifacts total: ${totalcount}" >> ${originDir}/checksum.log
echo -e " **** $(date '+%Y-%m-%d %H:%M:%S') - Artifacts total: ${totalcount}, Files total: ${wc}"

# set threads by FD
tmp_fifofile="/tmp/$$.fifo"
mkfifo $tmp_fifofile 
exec 6<>$tmp_fifofile
rm $tmp_fifofile
i=0
while [ $i -lt ${thread_num} ]; do
    echo
    i=$((i + 1))
done >&6


# 文件序列号
j=0
wc=$(ls ${StopTymd}.filelist_* | grep -v '.sha1' | wc -l)

# 遍历文件
for i in $(ls ${StopTymd}.filelist_* | grep -v '.sha1'); do
  j=$(($j + 1))
  # 处理每个文件
  (
    [ -f "${i}.sha1" ] || sha1sum -c ${i} > ${i}.sha1 2>/dev/null
    # 打印进度
    echo -e " **** $(date '+%Y-%m-%d %H:%M:%S') - Checking ${i} finished. \t ${j}/${wc}"
    sleep 1
    echo >&6
  ) &
done

# 等待所有后台进程完成
wait


# make a file for record checksum failed files
grep FAILED *.sha1 > ${StopTymd}checksum.error
failedcount=$(cat ${StopTymd}checksum.error|wc -l)
# print checksum failed
echo -e " **** \033[31mArtifacts checksum failed total: ${failedcount}\033[0m **** "
echo -e ",\t failed total: ${failedcount}" >> ${originDir}/checksum.log
 cat  ${StopTymd}checksum.error
exec 6>&-
Ubuntu new
#!/bin/sh
originDir=$(pwd)
touch checksum.conf checksum.log
. ./checksum.conf
if [ "${StopT+x}" ] ;then StartT=${StopT} ;else StartT="2000-01-01 00:01" ;fi
StopT=$(date '+%Y-%m-%d %H:%M')
StopTymd=$(date '+%Y-%m-%d')
echo "StartT=\"${StartT}\"" > checksum.conf
echo "StopT=\"${StopT}\"" >> checksum.conf
# file folder, should point filestore or filestore/33
baseDataDir="/opt/jfrog/artifactory/var/data/artifactory/filestore"
# lines of per file
perfilelines=10
# thread of checksum
thread_num=4

# Create a date folder for saving the checksum log
mkdir -p "/opt/${StopTymd}" && cd "/opt/${StopTymd}"
# Find files and save to filelist
printf "Finding artifacts from %s to %s\n" "${StartT}" "${StopT}" >> "${originDir}/checksum.log"
printf " **** %s - Finding artifacts **** \n" "$(date '+%Y-%m-%d %H:%M:%S')"
find "${baseDataDir}" -not \( -path ./_pre -prune \) -type f \( -newermt "${StartT}" -not -newermt "${StopT}" \) | gawk -F/ '/[a-fA-F0-9]{40}$/{print $NF,$0}' > "${StopTymd}.filelist"
# Check the total count
totalcount=$(wc -l < "${StopTymd}.filelist")

# split the large file
if [ -s "${StopTymd}.filelist" ]; then
  split -l "${perfilelines}" "${StopTymd}.filelist" -d -a 4 "${StopTymd}.filelist_"
else
  printf " **** Empty artifact list, exit script **** \n"
  printf "| Empty artifact list, exit script\n" >> "${originDir}/checksum.log"
  exit 1
fi
# files count
wc=$(ls ${StopTymd}.filelist_*|grep -v '.sha1'|wc -l)
# print split files count and total artifacts count
printf "| %s - Artifacts total: %d\n" "$(date '+%Y-%m-%d %H:%M')" "${totalcount}" >> "${originDir}/checksum.log"
printf " **** %s - Artifacts total: %d, Files total: %d\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${totalcount}" "${wc}"

# set threads by FD
fifo_file=$(mktemp /tmp/$$.fifo.XXXXXX)
# 删除已有的 FIFO 文件（如果存在）
if [ -e "$fifo_file" ]; then
  rm -f "$fifo_file"
fi

mkfifo "$fifo_file"

# 确保 FIFO 文件在脚本结束时被删除
cleanup() {
  rm -f "$fifo_file"
}
trap cleanup EXIT

# 设置并发线程数
exec 6<> "$fifo_file"
for _ in $(seq "$thread_num"); do
    echo
done >&6



# 文件序列号
j=0
wc=$(ls "${StopTymd}.filelist_"* | grep -v '.sha1' | wc -l)

# 遍历文件
for i in $(ls ${StopTymd}.filelist_* | grep -v '.sha1'); do
  j=$(($j + 1))
  # 处理每个文件
  (
    [ -f "${i}.sha1" ] || sha1sum -c "${i}" > "${i}.sha1" 2>/dev/null || shasum -a 1 "${i}" > "${i}.sha1" 2>/dev/null
    # 打印进度
    printf " **** %s - Checking %s finished. \t %d/%d\n" "$(date '+%Y-%m-%d %H:%M:%S')" "${i}" "${j}" "${wc}"
    sleep 1
    echo >&6
  ) &
done

# Wait for all background processes to complete
wait


# Record checksum failed files
grep FAILED *.sha1 > "${StopTymd}checksum.error"
failedcount=$(wc -l < "${StopTymd}checksum.error")
# print checksum failed
printf " **** \033[31mArtifacts checksum failed total: %d\033[0m **** \n" "${failedcount}"
printf ",\t failed total: %d\n" "${failedcount}" >> "${originDir}/checksum.log"
cat "${StopTymd}checksum.error"
exec 6>&-
