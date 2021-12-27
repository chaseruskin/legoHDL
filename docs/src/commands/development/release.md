# release

## Name

        release - Set a newer version for the current block

## Synopsis

        legohdl release <version> [-msg=<msg>] [-strict] [-dry-run] 
                [-no-changelog] [-no-install]

## Description

        :todo:

## Options

        <version>
                The next version for the current block. The value must be either
                major, minor, patch, or an explicit version.

        -msg=<msg>
                The message to commit with. The value for <msg> is a string and
                if the string includes spaces then quotes must encapsulate 
                <msg>. The default message is: "Releases legohdl version
                <version>".

        -strict
                Only adds and commits the modified changelog (if exists) and the
                Block.cfg file. All other uncommitted changes will not be in
                the following release.

        -dry-run
                Perform the complete release process as-if the block was to be
                released, but leaves the block unmodified and unreleased.

        -no-install
                Will not automatically install the latest version to the cache.

        -no-changelog
                Skip auto-opening a changelog file (if exists) during the
                release process.


