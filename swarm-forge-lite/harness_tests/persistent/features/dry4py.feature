Feature: dry4py

  Background:
    Given a temporary project with a source directory

  Scenario: dry4py 1 - no paths is a usage error
    When the dry4py command runs with no paths
    Then the dry4py command rejects the usage with exit code 2 and shows the usage

  Scenario: dry4py 2 - a missing path is refused
    Given a recording jscpd on the project PATH that reports no duplicates
    When the dry4py command runs with "missing.py"
    Then the dry4py command is refused with an error naming "missing.py"

  Scenario: dry4py 3 - a clean scan reports no duplicates
    Given a recording jscpd on the project PATH that reports no duplicates
    When the dry4py command runs with the source directory
    Then the dry4py command succeeds reporting no duplicate candidates

  Scenario: dry4py 4 - a dirty scan lists each duplicate pair and the count
    Given a recording jscpd on the project PATH that reports a duplicate from a.py lines 1-4 to b.py lines 1-4
    When the dry4py command runs with the source directory
    Then the dry4py command succeeds listing "a.py:1-4" and "b.py:1-4" and reporting 1 duplicate candidate

  Scenario: dry4py 5 - a scan with several duplicates counts them all
    Given a recording jscpd on the project PATH that reports a duplicate from a.py lines 1-4 to b.py lines 1-4
    And a duplicate from c.py lines 1-4 to d.py lines 1-4
    When the dry4py command runs with the source directory
    Then the dry4py command succeeds listing all four positions and reporting 2 duplicate candidates

  Scenario Outline: dry4py 6 - the scan thresholds are passed to jscpd
    Given a recording jscpd on the project PATH that reports no duplicates
    When the dry4py command runs with threshold flags "--min-lines" <min_lines> and "--min-tokens" <min_tokens> over the source directory
    Then the dry4py command succeeds with the recording jscpd run with "--min-lines" <min_lines> and "--min-tokens" <min_tokens>

    Examples:
      | min_lines | min_tokens |
      | 4         | 50         |
      | 6         | 20         |

  Scenario: dry4py 7 - the default thresholds are passed to jscpd
    Given a recording jscpd on the project PATH that reports no duplicates
    When the dry4py command runs with the source directory and no threshold flags
    Then the dry4py command succeeds with the recording jscpd run with "--min-lines" 4 and "--min-tokens" 50

  Scenario Outline: dry4py 8 - a non-positive threshold is refused
    Given a recording jscpd on the project PATH that reports no duplicates
    When the dry4py command runs with the threshold <flag> 0 over the source directory
    Then the dry4py command is refused with an error naming <name>

    Examples:
      | flag         | name       |
      | --min-lines  | min_lines  |
      | --min-tokens | min_tokens |

  Scenario: dry4py 9 - a threshold of one line is accepted
    Given a recording jscpd on the project PATH that reports no duplicates
    When the dry4py command runs with the threshold "--min-lines" 1 over the source directory
    Then the dry4py command succeeds with the recording jscpd run with "--min-lines" 1

  Scenario: dry4py 10 - a missing jscpd is refused
    Given no jscpd on the project PATH
    When the dry4py command runs with the source directory
    Then the dry4py command is refused with an error saying the detector command was not found

  Scenario: dry4py 11 - a failing jscpd is refused
    Given a recording jscpd on the project PATH that prints "boom" and exits with status 3
    When the dry4py command runs with the source directory
    Then the dry4py command is refused with an error reporting "boom"

  Scenario: dry4py 12 - a jscpd exit status of one is accepted
    Given a recording jscpd on the project PATH that reports no duplicates and exits with status 1
    When the dry4py command runs with the source directory
    Then the dry4py command succeeds reporting no duplicate candidates

  Scenario: dry4py 13 - a detector that writes no report is refused
    Given a recording jscpd on the project PATH that writes no report
    When the dry4py command runs with the source directory
    Then the dry4py command is refused with an error saying the detector produced no report

  Scenario: dry4py 14 - a detector report that is not JSON is refused
    Given a recording jscpd on the project PATH that writes "not json" as its report
    When the dry4py command runs with the source directory
    Then the dry4py command is refused with an error saying the report is not valid JSON

  Scenario: dry4py 15 - a detector report without a duplicate list is refused
    Given a recording jscpd on the project PATH that writes "{}" as its report
    When the dry4py command runs with the source directory
    Then the dry4py command is refused with an error saying the report has no duplicate list
