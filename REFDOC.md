# Refactoring documentation  
> Warning: this documentation is not yet completed. It will be completed gradually over time.  

> Note: attributes are to be assumed private and methods are to be assumed public, unless noted otherwise.  

> Note: attributes and methods noted as "private" are actually accessible, but the direct access of them is strongly discouraged and may results in random bugs after future refactoring.  

> Note: methods return `None` unless noted otherwise.  

> Note: for implementation details involving lock operations, `acquire ... release`
may be implemented as either `acquire ... release`, `acquire try ... finally`, or `with ...`.

> Warning: if the last change time indicated in this documentation is earlier
than that indicated in corresponding code sections, this documentation is out of sync (and hence almost useless).

# File globalvars.py  
## Class GlobalVars.PostScanStat  
Tracking post scanning data.  
### Public interface  
- `add_stat(posts_scanned, scan_time)`: Add `posts_scanned` to total numbers of posts scanned. Add `scan_time` to total time spent on scanning.
- `get_stat()`: Get total numbers of posts scanned, total time spent on scanning and posts scanned per second.
If total time spent is zero, posts scanned per second is set to `None`. Returns a tuple `(posts_scanned, scan_time, posts_per_second)`.
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
- `get_stat()`: Obtain `rw_lock`. Read `num_posts_scanned` into `posts_scanned`. Read `post_scan_time` into `scan_time`. Release `rw_lock`.
Decide if `scan_time` is `0`. If yes, set `posts_per_second` to `None`. Otherwise calculate `posts_per_second` as `posts_scanned` divided by `scan_time`.
Return a tuple `(posts_scanned, scan_time, posts_per_second)`.
- `snap()`: Obtain `rw_lock`. Set `snap_num_posts_scanned` to `num_posts_scanned`. Set `snap_post_scan_time` to `post_scan_time`. Release `rw_lock`.
- `get_snap()`: Obtain `rw_lock`. Read `snap_num_posts_scanned` into `snap_posts_scanned`. Read `snap_post_scan_time` into `snap_scan_time`. Release `rw_lock`.
Decide if `snap_scan_time` is `0`. If yes, set `snap_posts_per_second` to `None`. Otherwise calculate `snap_posts_per_second` as `snap_posts_scanned` divided by `snap_scan_time`.
Return a tuple `(snap_posts_scanned, snap_scan_time, snap_posts_per_second)`.
- `reset_stat()`: Obtain `rw_lock`. Set `num_posts_scanned` and `post_scan_time` to `0`. Release `rw_lock`.
- `reset_snap()`: Obtain `rw_lock`. Set `snap_num_posts_scanned` and `snap_post_scan_time` to `0`. Release `rw_lock`.
#### Considerations  
- Both read and write operations are lock protected,
as it is necessary to perform thread safe write and to prevent reading while another thread is writing.
### Known bugs  
- None
> Last change in this section was on 19 May 2020.  
## Class GlobalVars.MSStatus  
Tracking metasmoke status.  
### Public interface  
- `is_up()`: Query if metasmoke is up. Returns `True` if metasmoke is up and `False` otherwise.
- `is_down()`: Query if metasmoke is down. Returns `True` if metasmoke is down and `False` otherwise.
- `failed()`: Indicate a metasmoke connection failure.
- `succeeded()`: Indicate a metasmoke connection success.
- `get_failure_count()`: Get metasmoke connection failure counter value. The counter counts consecutive failures.
- `reset_ms_status()`: Reset class `GlobalVars.ms_status` to default values.
### Thread safety  
Yes.  
### Notes on usage  
- Metasmoke counter represents consecutive metasmoke failures.
### Implementation  
This class is implemented with 2 static variables and 1 lock.  
#### Details  
##### Attributes  
- `ms_is_up`: Whether or not metasmoke is up.
- `counter`: Metasmoke connection failure counter.
- `rw_lock`: Lock. Controlling access to `ms_is_up`, `failure_count` and `last_ping_time`.
##### Methods  
- `set_up()`: Private to `metasmoke.py`. Obtain `rw_lock`. Set `ms_is_up` to `True`. Release `rw_lock`.
- `set_down()`: Private to `metasmoke.py`. Obtain `rw_lock`. Set `ms_is_up` to `False`. Release `rw_lock`.
- `is_up()`: Obtain `rw_lock`. Read `ms_is_up` into `current_ms_status`. Release `rw_lock`. Return `current_ms_status`.
- `is_down()`: Call `is_up()` and return the inverted returned value.
- `failed()`: Obtain `rw_lock`. Increase `counter` by `1`. Release `rw_lock`.
- `succeeded()`: Obtain `rw_lock`. Set `counter` to `0`. Release `rw_lock`.
- `get_failure_count()`: Obtain `rw_lock`. Read `counter` into `current_counter`. Release `rw_lock`. Return `current_failure_count`.
- `reset_ms_status`: Obtain `rw_lock`. Set `ms_is_up` to `True`. Set `counter` to `0`. Release `rw_lock`.
#### Considerations  
- `is_down()` is implemented to call `is_up()`, so maintainance tasks only need to be performed on `is_up()`.
### Known bugs  
- None.
> Last change in this section was on 20 May 2020.
# File metasmoke.py  
## Class Metasmoke  
> Note: the documentation of this class is not yet completed.
### Subclasses  
- `AutoSwitch`
### Public interface  
- `ms_up()`: Switch metasmoke status to up.
- `ms_down()`: Switch metasmoke status to down.
> Not completed yet.
### Thread safety  
Unknown. The component currently documented in public interface is thread safe.  
### Notes on usage  
- Unless there are good reasons, always call `Metasmoke.ms_up()` and `Metasmoke.ms_down()`
instead of `GlobalVars.MSStatus.set_up()` and `GlobalVars.MSStatus.set_down()`.
The former is a wrapper of the latter which offers logging and chat messages.
### Implementation  
> Not completed yet.
### Known bugs  
- None.
> Last change in this section was on 20 May 2020.
## Class Metasmoke.AutoSwitch  
Automatically switch metasmoke status.
### Public interface  
- `to_off()`: Indicate a status ping failure.
- `to_on()`: Indicate a status ping success.
- `switch_auto(on)`: Turn on or off auto switch.
If `on` is `True`, auto switch is turned on. Otherwise auto switch is turned off.
- `reset_switch()`: Reset class `Metasmoke.AutoSwitch` to default values.
### Thread safety  
Yes.  
### Notes on usage  
- Failures or successes contributing to auto switching of metasmoke status should be those of status ping.
Other failures or successes should not trigger auto switch.
### Implementation  
This class is implemented with 2 constants, 2 static variables and 1 lock.  
#### Details
##### Attributes  
- `MAX_FAILURES`: Maximum failures before metasmoke status is switched down.
- `MAX_SUCCESSES`: Maximum successes before metasmoke status is switched up.
- `counter`: Consecutive failure and success counter.
A negative value represents successes while a positive value represents failures.
- `auto`: Whether or not to perform auto switch.
- `rw_lock`: Lock. Controlling access to `counter` and `auto`.
##### Methods  
- `to_off()`: Obtain `rw_lock`. Decide if `counter` is negative. If yes, set `counter` to `0`.
Increase `counter` by `1`. Read `counter` into `current_counter`. Read `auto` into `current_auto`. Release `rw_lock`.
Decide if `current_counter` is greater than `MAX_FAILURES`, metasmoke status is up, and `current_auto` is `True`.
If yes, issue a message to chat and call `ms_down()`.
- `to_on()`: Obtain `rw_lock`. Decide if `counter` is positive. If yes, set `counter` to `0`.
Decrease `counter` by `1`. Read `-counter` into `current_counter`. Read `auto` into `current_auto`. Release `rw_lock`.
Decide if `current_counter` is greater than `MAX_SUCCESSES`, metasmoke status is down, and `current_auto` is `True`.
If yes, issue a message to chat and call `ms_up()`.
- `switch_auto(on)`: Obtain `rw_lock`. Set `auto` to `on`. Release `rw_lock`.
- `reset_switch()`: Obtain `rw_lock`. Set `counter` to `0`. Set `auto` to `True`. Release `rw_lock`.
#### Considerations  
- Only status ping failures and successes should count, as otherwise it will be unbalanced
since after metasmoke is declared down, only status pings are sent.
However this cannot be enforced within the class,
so please take this into consideration when calling `to_on()` and `to_off()`.
### Known bugs  
- None.
> Last change in this section was on 20 May 2020.
# Special cases
## File socketscience.py, in class SocketScience
- On line 78 and 87, `GlobalVars.MSStatus.set_up()` and `GlobalVars.MSStatus.set_down()` is called.
This is to prevent circular import between `Metasmoke` and `SocketScience`. (20 May 2020)
