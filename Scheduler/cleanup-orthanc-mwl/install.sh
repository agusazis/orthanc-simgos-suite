#!/bin/sh

chmod +x run.sh

cat > /etc/cron.d/cleanup-orthanc-mwl <<-EOF
0 1 * * * root /opt/orthanc/Scheduler/cleanup-orthanc-mwl/run.sh
EOF
