# TODO List
## Bugs
- [ ] GUI - start scan starts two scans
  - Maybe on see one api call but two dirs
## Current Improvments
- [x] ~~Go through the code and add comments~~
- [x] ~~Go through scraper README~~
- [x] ~~Refer to scraper README in main README~~
- [ ] Implement error handling for AWS API calls
- [x] ~~Add unit tests~~
- [ ] Check that start API calls aren't blocked
- [x] ~~Check that API calls are idempotent~~
- [ ] Add verbose to aws-list-all (default true)

## Future Tasks
- [ ] Use `aws-list-all introspect list-operations` to build and save services operations
  - It would be useful to have a list of all operations available in the service
  - Enables incremental scrapes
  - Helps deal with failed invocations
