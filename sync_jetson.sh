# !/bin/bash
while true; do
    rsync -azhve ssh edhitha@192.168.1.28:/home/edhitha/DCIM/test_cam/images /Users/aahil/Edhitha/edhithaGCS-main-UI/Data/Test/
    sleep 1
done

# rsync: A tool for syncing files/directories between machines.
#-a: Archive mode – preserves file permissions, timestamps, symbolic links, etc.
#-z: Compresses files during transfer to save bandwidth.
#-h: Human-readable – shows file sizes in readable units (KB, MB, etc.).
#-v: Verbose – prints out details of the transfer.
#-e ssh: Uses SSH (secure shell) for secure file transfer.