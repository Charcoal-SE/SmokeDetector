### Requirements when making Code Changes (NOT watchlist/blacklist changes)

When submitting a pull request to the SmokeDetector code base, the
Charcoal team needs the pull request to contain enough information for us to 
quickly review the PR, without requiring in-depth code analysis.

**As such, a pull request that suggests code changes** (NOT blacklist or 
watchlist changes) must have all or most of the following information:

1. What does your pull request change or introduce to the project?
2. What is the justification for the inclusion of your Pull Request (or, what 
   problem does it solve?)
3. What does your code (if new) actually do?  Summarize what your new code 
   does (either within the code via comments or with your Pull Request)
4. Include comments in your code to help guide reviewers through what
   you intend for the sub-portions of your code to be doing. It's a
   _lot_ easier to review code when you have a general idea of what
   the intended functionality of a section of code is. It also helps
   as a double-check that the code is doing what is intended. Commenting
   doesn't need to be extensive, but should be present sufficiently
   to guide a reviewer/reader/maintainer.
5. Use meaningful variable names. Variable names should reflect what
   the contents of that variable is, or what it represents. This helps
   significantly in making your code self-documenting. Using meaningful
   variable names can significantly reduce the need for code comments.
6. What testing have you done?
   - Are you relying solely on the CircleCI and Travis CI testing?
   - Have you spun up a SmokeDetector instance on which you've run the
     code in the PR and verified that the it's actually doing what you
     intend/expect?

   This doesn't represent a *requirement* that you do extensive testing,
   but we need to know the outline of what and how much testing you've
   done, so we can evaluate what testing still needs to be performed prior
   to merging. Obviously, the more extensive the change, the more testing
   is desirable. The testing required can be anywhere between none to
   quite a bit, depending on the changes being made.
   
Pull requests that do not have ample information attached to them for 
justification, etc. may be rejected or may be put on hold until we get more 
information. Failure to provide ample information will result in delayed 
processing times.

### Requirements when making Watchlist/Blacklist changes

Changes to watchlists or blacklists are simpler to process. A simple 
justification for why it should be included/changed is all you really need,
unless the change or regex(es) are complex. However, if it's that complex,
then a watchlist entry may not be the most appropriate way to implement
the detection. OTOH, that doesn't preclude using the watchlist to gather
data.
