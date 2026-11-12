---
product: storage
updated: 2026
---
# Storage service

## Limits
The Free plan includes 5 GB of storage. The Team plan includes 1 TB per workspace. The maximum size of a single file is 50 GB on all plans. Uploads above 5 GB must use the multipart upload API.

## Error STG-507
Error code STG-507 means the workspace has reached its storage quota. Uploads fail until files are deleted or the plan is upgraded. Deleted files stay in the trash for 30 days and still count toward the quota until the trash is emptied.

## Versioning
File versioning keeps the last 100 versions of each file for 90 days. Versions older than 90 days are removed automatically. Restoring a version creates a new version; it does not delete newer ones.

## Regions
Data is stored in the region chosen when the workspace is created: us-east, eu-west or ap-south. A workspace cannot change region after creation; data must be exported and imported into a new workspace.
