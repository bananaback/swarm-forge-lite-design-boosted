Feature: Harness CLI

  Background:
    Given no harness environment overrides

  Scenario Outline: Harness CLI 1 - config prints each resolved wiring field
    Given a temporary project with its own harness config and roots inside it
    When the harness config command runs
    Then the config output has a <field> field

    Examples:
      | field            |
      | pack_root        |
      | workspace_root   |
      | state_root       |
      | artifacts_root   |
      | hot_tests        |
      | persistent_tests |
      | source_roots     |
      | features         |
      | config_path      |

  Scenario: Harness CLI 2 - config resolves the roots inside the project
    Given a temporary project with its own harness config and roots inside it
    When the harness config command runs
    Then the config output places the workspace, state, artifacts, and hot roots inside the project directory

  Scenario: Harness CLI 3 - status reports a row for every resolved root
    Given a temporary project with its own harness config and roots inside it
    When the harness status command runs
    Then the status reports a row for each of the pack, config, workspace, state, artifacts, hot, features, source, and persistent roots

  Scenario Outline: Harness CLI 4 - status marks each resolved row present or missing
    Given a temporary project whose source and persistent roots are present and whose workspace, state, artifacts, hot, and features roots are absent
    When the harness status command runs
    Then the status marks the <row> row as "<marker>"

    Examples:
      | row       | marker |
      | PACK      | ok     |
      | CONFIG    | ok     |
      | WORKSPACE | -      |
      | STATE     | -      |
      | ARTIFACTS | -      |
      | HOT       | -      |
      | FEATURES  | -      |
      | SOURCE    | ok     |
      | PERSIST   | ok     |

  Scenario Outline: Harness CLI 5 - clean empties the named managed area
    Given a temporary project with all harness roots inside it
    And a generated file under the project <area> directory
    When the harness clean command runs for <area>
    Then the harness command succeeds with the project <area> directory empty

    Examples:
      | area      |
      | hot       |
      | artifacts |
      | state     |

  Scenario Outline: Harness CLI 6 - clean all empties hot, artifacts, and state
    Given a temporary project with all harness roots inside it
    And a generated file under each of the hot, artifacts, and state directories
    When the harness clean command clears every managed area
    Then the harness command succeeds with the project <area> directory empty

    Examples:
      | area      |
      | hot       |
      | artifacts |
      | state     |

  Scenario: Harness CLI 7 - clean with no target empties the hot area
    Given a temporary project with all harness roots inside it
    And a generated file under the project hot directory
    When the harness clean command runs without a target
    Then the harness command succeeds with the project hot directory empty

  Scenario: Harness CLI 8 - clean leaves the other managed areas untouched
    Given a temporary project with all harness roots inside it
    And a generated file under each of the hot, artifacts, and state directories
    When the harness clean command runs for artifacts
    Then the hot and state directories still hold their generated files

  Scenario Outline: Harness CLI 9 - clean reports the removed entry count
    Given a temporary project with <count> generated files under the hot directory
    When the harness clean command runs against the hot area
    Then the harness command succeeds reporting the removed entry count as <count>

    Examples:
      | count |
      | 1     |
      | 3     |

  Scenario: Harness CLI 10 - clean on an absent area reports nothing removed
    Given a temporary project with all harness roots inside it and the hot directory absent
    When the harness clean command runs against the hot area
    Then the harness command succeeds reporting the removed entry count as 0

  Scenario: Harness CLI 11 - an unknown clean target is refused
    Given a temporary project with all harness roots inside it
    When the harness clean command runs for the unknown target "bogus"
    Then the harness command is refused with exit code 2 and an error naming "bogus"

  Scenario: Harness CLI 12 - a missing config is refused by status
    Given a temporary project whose config path is missing
    When the harness status command runs with that missing config
    Then the harness command is refused with exit code 2 and an error naming the missing config

  Scenario: Harness CLI 13 - a missing config is refused by config
    Given a temporary project whose config path is missing
    When the harness config command runs with that missing config
    Then the harness command is refused with exit code 2 and an error naming the missing config

  Scenario: Harness CLI 14 - a missing config is refused by clean
    Given a temporary project whose config path is missing
    When the harness clean command runs with that missing config for the hot area
    Then the harness command is refused with exit code 2 and an error naming the missing config

  Scenario: Harness CLI 15 - an unconfigured features root is absent
    Given a temporary project with its roots inside it and no features root configured
    When the harness status command runs
    Then the status reports the FEATURES row as absent

  Scenario: Harness CLI 16 - multiple source roots render one row each
    Given a temporary project with two source roots inside it
    When the harness status command runs
    Then the status reports two SOURCE rows
