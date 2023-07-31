DB_NAME="almalinux"
# 2023-01-09_almalinux.dump
DUMP_NAME="$(date -I)_$DB_NAME.dump"
DUMP_PATH="/srv/$DUMP_NAME"

AZURE_BLOB_TOKEN=""
AZURE_BLOB_CONTAINER="backups"
AZURE_BLOB_URL="https://almabuildsys.blob.core.windows.net"
AZURE_BLOB_UPLOAD_URL="$AZURE_BLOB_URL/$AZURE_BLOB_CONTAINER/$DUMP_NAME?$AZURE_BLOB_TOKEN"

pg_dump -Fc -d $DB_NAME > $DUMP_PATH
azcopy copy "$DUMP_PATH" "$AZURE_BLOB_UPLOAD_URL" --put-md5=true
rm $DUMP_PATH
