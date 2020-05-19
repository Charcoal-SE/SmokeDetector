# Refactoring documentation  
> Warning: this documentation is not yet completed. It will be completed gradually over time.  

> Note: attributes are to be assumed private and methods are to be assumed public, unless noted otherwise.  

> Note: attributes and methods noted as "private" are actually accessible, but the direct access of them is strongly discouraged and may results in random bugs after future refactoring.  

> Note: methods return `None` unless noted otherwise.  

> Warning: if the last change time indicated in this documentation is earlier than that indicated in corresponding code sections, this documentation is out of sync (and hence almost useless).

# File globalvars.py  
## Class GlobalVars.PostScanStat  
Tracking post scanning data.  
### Public interface  
- `add_stat(posts_scanned, scan_time)`: Add `posts_scanned` to total numbers of posts scanned. Add `scan_time` to total time spent on scanning.
- `get_stat()`: Get total numbers of posts scanned, total time spent on scanning and posts scanned per second. If total time spent is zero, posts scanned per second is set to `None`. Returns a tuple `(posts_scanned, scan_time, posts_per_second)`.
- `snap()`: Take a snapshot of current post scanning data. Will overwrite last snapshot.
- `get_snap()`: Get the snapshot of post scanning data.
- `reset_stat()`: Reset post scanning data, which includes total numbers of posts scanned and total time spent on scanning to `0`.
- `reset_snap()`: Reset snapshot data.
### Thread safety  
Yes.  
### Notes on usage
- None.
### Implementation
This class is implemented with 4 static variables and 1 lock.  
#### Details
##### Attributes  
- `num_posts_scanned`: Tracking total numbers of posts scanned.
- `post_scan_time`: Tracking total time spent on scanning.
- `snap_num_posts_scanned`: Snapshot of `num_posts_scanned`.
- `snap_post_scan_time`: Snapshot of `post_scan_time`.
- `rw_lock`: Lock. Controlling access to `num_posts_scanned`, `post_scan_time`, `snap_num_posts_scanned` and `snap_post_scan_time`.
##### Methods  
- `add_stat(posts_scanned, scan_time)`: Obtain `rw_lock`. Add `posts_scanned` and `scan_time` to `num_posts_scanned` and `post_scan_time`. Release `rw_lock`.
- `get_stat()`: Obtain `rw_lock`. Read `num_posts_scanned` into `posts_scanned`. Read `post_scan_time` into `scan_time`. Release `rw_lock`. Decide if `scan_time` is `0`. If yes, set `posts_per_second` to `None`. Otherwise calculate `posts_per_second` as `posts_scanned` divided by `scan_time`. Return a tuple `(posts_scanned, scan_time, posts_per_second)`.
- `snap()`: Obtain `rw_lock`. Set `snap_num_posts_scanned` to `num_posts_scanned`. Set `snap_post_scan_time` to `post_scan_time`. Release `rw_lock`.
- `get_snap()`: Obtain `rw_lock`. Read `snap_num_posts_scanned` into `snap_posts_scanned`. Read `snap_post_scan_time` into `snap_scan_time`. Release `rw_lock`. Decide if `snap_scan_time` is `0`. If yes, set `snap_posts_per_second` to `None`. Otherwise calculate `snap_posts_per_second` as `snap_posts_scanned` divided by `snap_scan_time`. Return a tuple `(snap_posts_scanned, snap_scan_time, snap_posts_per_second)`.
- `reset_stat()`: Obtain `rw_lock`. Set `num_posts_scanned` and `post_scan_time` to `0`. Release `rw_lock`.
- `reset_snap()`: Obtain `rw_lock`. Set `snap_num_posts_scanned` and `snap_post_scan_time` to `0`. Release `rw_lock`.
#### Considerations  
- Both read and write operations are lock protected, as it is necessary to perform thread safe write and to prevent reading while another thread is writing.
### Known bugs  
- None
> Last change in this section was on 19 May 2020.  
