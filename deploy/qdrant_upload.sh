# git actions에서 snapshot 선택 후 재빌드 하거나 아래 명령어 실행하거나 둘 중 하나.
# 1. S3에서 스냅샷 다운로드
aws s3 cp s3://triver-assets-prod/private/snapshots/photos.snapshot.tar /tmp/photos.snapshot
aws s3 cp s3://triver-assets-prod/private/snapshots/places.snapshot.tar /tmp/places.snapshot

# 2. Qdrant 복원
curl -X POST "http://localhost:6333/collections/places/snapshots/upload?priority=snapshot" \
  -H "Content-Type: multipart/form-data" \
  -F "snapshot=@/tmp/places.snapshot"

curl -X POST "http://localhost:6333/collections/photos/snapshots/upload?priority=snapshot" \
  -H "Content-Type: multipart/form-data" \
  -F "snapshot=@/tmp/photos.snapshot"

# 3. 복원 확인
curl http://localhost:6333/collections/places
curl http://localhost:6333/collections/photos
