#!/bin/sh

chmod +x reset_mover.sh

cat > /etc/cron.d/reset_mover <<-EOF
00 01 * * * * root /opt/dicom-mover/cron-job/reset_mover.sh
EOF
