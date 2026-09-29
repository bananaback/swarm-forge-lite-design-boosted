Feature: ruff4py

  Background:
    Given a temporary project with a harness config and an artifacts root

  Scenario Outline: ruff4py 1 - help prints the wrapper usage without running ruff
    Given a recording ruff on the project PATH that succeeds
    When the ruff4py command runs with "<flag>"
    Then the ruff4py command succeeds showing the wrapper usage and the recording ruff was never invoked

    Examples:
      | flag   |
      | --help |
      | -h     |

  Scenario: ruff4py 2 - an explicit check verb is refused
    Given a recording ruff on the project PATH that succeeds
    When the ruff4py command runs with an explicit "check" verb and "tools"
    Then the ruff4py command is refused with exit code 2 saying that check is already supplied

  Scenario Outline: ruff4py 3 - the ruff exit status passes through
    Given a recording ruff on the project PATH that exits with status <status>
    When the ruff4py command runs with "tools"
    Then ruff4py exits with code <status>

    Examples:
      | status |
      | 0      |
      | 1      |
      | 2      |

  Scenario: ruff4py 4 - the wrapper supplies its verb, cache directory, and config
    Given a recording ruff on the project PATH that succeeds
    When the ruff4py command runs with "tools"
    Then the recording ruff was run with "check", the wrapper cache directory, the pack ruff config, and "tools"

  Scenario: ruff4py 5 - the wrapper creates its cache directory
    Given a recording ruff on the project PATH that succeeds
    And the wrapper cache directory does not exist
    When the ruff4py command runs with "tools"
    Then the wrapper cache directory exists

  Scenario Outline: ruff4py 6 - a caller option is not replaced
    Given a recording ruff on the project PATH that succeeds
    When the ruff4py command runs with the caller option <option> <value> and "tools"
    Then the recording ruff was run with <value> once and not run with the wrapper <absent>

    Examples:
      | option      | value        | absent           |
      | --cache-dir | caller-cache | cache directory  |
      | --config    | caller.toml  | pack ruff config |

  Scenario: ruff4py 7 - a caller option in equals form is not replaced
    Given a recording ruff on the project PATH that succeeds
    When the ruff4py command runs with the caller option "--config=caller.toml" and "tools"
    Then the recording ruff was run with "--config=caller.toml" once and not run with the pack ruff config

  Scenario: ruff4py 8 - RUFF4PY_CONFIG overrides the pack config
    Given a recording ruff on the project PATH that succeeds
    And the environment sets RUFF4PY_CONFIG to "custom.toml"
    When the ruff4py command runs with "tools"
    Then the recording ruff used "custom.toml" as its config

  Scenario: ruff4py 9 - a missing ruff is refused
    Given no ruff on the project PATH
    When the ruff4py command runs with "tools"
    Then the ruff4py command is refused with exit code 2 saying ruff is not installed

  Scenario: ruff4py 10 - a missing pack config is refused
    Given a recording ruff on the project PATH that succeeds
    And no pack ruff config
    When the ruff4py command runs with "tools"
    Then the ruff4py command is refused with exit code 2 naming the missing ruff config

  Scenario: ruff4py 11 - a missing override config is refused
    Given a recording ruff on the project PATH that succeeds
    And the environment sets RUFF4PY_CONFIG to "missing.toml"
    When the ruff4py command runs with "tools"
    Then the ruff4py command is refused with exit code 2 naming the missing ruff config

  Scenario: ruff4py 12 - an unrunnable ruff is refused
    Given a ruff on the project PATH that cannot be executed
    When the ruff4py command runs with "tools"
    Then the ruff4py command is refused with exit code 2 saying ruff cannot be run

  Scenario: ruff4py 13 - a missing harness config is refused
    Given a recording ruff on the project PATH that succeeds
    And the harness config is missing
    When the ruff4py command runs with "tools"
    Then the ruff4py command is refused with exit code 2 naming the missing harness config
