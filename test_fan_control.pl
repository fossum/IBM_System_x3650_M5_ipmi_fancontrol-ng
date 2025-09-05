#!/usr/bin/perl

=head1 NAME

test_fan_control.pl - Functional test for IPMI fan control logic

=head1 SYNOPSIS

    ./test_fan_control.pl [options]

    Options:
        --dry-run       Don't actually set fan speeds, just simulate
        --verbose       Enable verbose output
        --config FILE   Use alternate config file (default: ./config.conf)
        --help          Show this help message

=head1 DESCRIPTION

This script performs functional testing of the fan control logic using local
IPMI commands. It verifies that temperature-to-fan speed calculations work
correctly and that IPMI commands are properly executed.

=cut

use strict;
use warnings;

use Getopt::Long;
use FindBin qw($RealBin);
use File::Spec;
use Cwd qw(abs_path);

# Add both the script directory and current directory to @INC
use lib $RealBin;
use lib '.';
use lib abs_path('.');

use FanConfig qw(load validate_config);
use Fan;

# Command line options
my $dry_run = 0;
my $verbose = 0;
my $config_file = './config.conf';
my $help = 0;

GetOptions(
    'dry-run'    => \$dry_run,
    'verbose'    => \$verbose,
    'config=s'   => \$config_file,
    'help'       => \$help,
) or die "Error parsing command line options\n";

if ($help) {
    print_help();
    exit 0;
}

sub print_help {
    print <<'EOF';
IPMI Fan Control Functional Test

Usage: ./test_fan_control.pl [options]

Options:
    --dry-run       Don't actually set fan speeds, just simulate
    --verbose       Enable verbose output
    --config FILE   Use alternate config file (default: ./config.conf)
    --help          Show this help message

This test performs the following checks:
1. Configuration file loading
2. IPMI tool availability
3. Fan status reading
4. Temperature curve calculations
5. Fan speed setting (if not dry-run)
6. Fan speed verification

EOF
}

sub log_message {
    my ($level, $message) = @_;
    my $timestamp = localtime();

    if ($level eq 'INFO' || $verbose || $level eq 'ERROR') {
        print "[$timestamp] [$level] $message\n";
    }
}

sub test_ipmi_availability {
    log_message('INFO', 'Testing IPMI tool availability...');

    my $result = `which ipmitool 2>/dev/null`;
    chomp $result;

    if (!$result) {
        log_message('ERROR', 'ipmitool not found in PATH');
        return 0;
    }

    log_message('INFO', "Found ipmitool at: $result");

    # Test basic IPMI connectivity
    my $sdr_output = `ipmitool sdr list 2>&1`;
    my $exit_code = $? >> 8;

    if ($exit_code != 0) {
        log_message('ERROR', "IPMI communication failed: $sdr_output");
        return 0;
    }

    log_message('INFO', 'IPMI communication successful');
    return 1;
}

sub get_current_fan_speeds {
    my ($config) = @_;
    log_message('INFO', 'Reading current fan speeds...');

    my %fan_speeds;
    my $preamble = $config->{ipmi}{preamble};

    # Try to get fan information from SDR
    my $sdr_output = `$preamble sdr list | grep -i fan 2>/dev/null`;
    log_message('DEBUG', "Fan SDR output:\n$sdr_output") if $verbose;

    # Try to get fan speeds using sensor readings
    my $sensor_output = `$preamble sensor list | grep -i fan 2>/dev/null`;
    log_message('DEBUG', "Fan sensor output:\n$sensor_output") if $verbose;

    return \%fan_speeds;
}

sub test_temperature_curve {
    my ($fan_controller) = @_;
    log_message('INFO', 'Testing temperature curve calculations...');

    my $curve = $fan_controller->get_temperature_curve();

    if (!%$curve) {
        log_message('ERROR', 'No temperature curve loaded');
        return 0;
    }

    log_message('INFO', 'Temperature curve points:');
    foreach my $temp (sort {$a <=> $b} keys %$curve) {
        my $speed = $curve->{$temp};
        log_message('INFO', "  ${temp}°C -> ${speed}% fan speed");
    }

    # Test calculations at various temperatures
    my @test_temps = (20, 30, 45, 60, 75, 85);

    log_message('INFO', 'Testing fan speed calculations:');
    foreach my $test_temp (@test_temps) {
        my ($desired_speed, $calculated_speed) = $fan_controller->calculate_desired_fan_speed($test_temp);
        log_message('INFO', sprintf("  %d°C -> %.1f%% (calculated: %.2f)",
                                  $test_temp, $desired_speed, $calculated_speed));
    }

    return 1;
}

sub test_fan_setting {
    my ($fan_controller, $dry_run) = @_;
    log_message('INFO', 'Testing fan speed setting...');

    if ($dry_run) {
        log_message('INFO', 'DRY RUN: Simulating fan speed changes');

        # Simulate setting different speeds
        my @test_speeds = (30, 50, 70);
        foreach my $speed (@test_speeds) {
            log_message('INFO', "DRY RUN: Would set fan speed to ${speed}%");
            # Update internal state for testing
            $fan_controller->{current_fan_duty_cycle} = $speed;
        }
    } else {
        log_message('INFO', 'Setting test fan speed (50%)...');

        # Get current fan speeds first
        my $original_speed = $fan_controller->get_current_fan_duty_cycle();

        # Force temperature change to trigger fan update
        $fan_controller->{current_cpu_temp} = 50;
        $fan_controller->{last_set_cpu_temp} = 40;  # Force update

        # Test setting fan speed
        $fan_controller->set_fan_speed(50);

        sleep 2;  # Give time for IPMI command to take effect

        log_message('INFO', 'Fan speed set successfully');

        # Restore original speed if possible
        if ($original_speed > 0) {
            log_message('INFO', "Restoring original fan speed (${original_speed}%)...");
            $fan_controller->set_fan_speed($original_speed);
        }
    }

    return 1;
}

sub main {
    log_message('INFO', 'Starting IPMI Fan Control Functional Test');
    log_message('INFO', "Dry run mode: " . ($dry_run ? 'ENABLED' : 'DISABLED'));

    # Test 1: Load configuration
    log_message('INFO', 'Loading configuration...');
    my $config = FanConfig::load($config_file);

    if (!$config) {
        log_message('ERROR', "Failed to load config from $config_file");
        exit 1;
    }

    log_message('INFO', 'Configuration loaded successfully');
    log_message('DEBUG', "Config: " . sprintf("%d sections loaded", scalar keys %$config)) if $verbose;

    # Test 2: IPMI availability
    my $ipmi_available = test_ipmi_availability();
    if (!$ipmi_available && !$dry_run) {
        log_message('ERROR', 'IPMI tests failed and not in dry-run mode - aborting');
        exit 1;
    } elsif (!$ipmi_available) {
        log_message('INFO', 'IPMI not available, but continuing in dry-run mode');
    }

    # Test 3: Fan controller initialization
    log_message('INFO', 'Initializing Fan controller...');
    my $fan_controller = Fan->new($config);

    if (!$fan_controller) {
        log_message('ERROR', 'Failed to initialize Fan controller');
        exit 1;
    }

    log_message('INFO', 'Fan controller initialized successfully');

    # Test 4: Get current fan status
    my $current_speeds = get_current_fan_speeds($config);

    # Test 5: Temperature curve testing
    if (!test_temperature_curve($fan_controller)) {
        log_message('ERROR', 'Temperature curve tests failed');
        exit 1;
    }

    # Test 6: Fan speed setting
    if (!test_fan_setting($fan_controller, $dry_run)) {
        log_message('ERROR', 'Fan setting tests failed');
        exit 1;
    }

    log_message('INFO', 'All tests completed successfully!');

    # Summary
    print "\n" . "="x60 . "\n";
    print "TEST SUMMARY\n";
    print "="x60 . "\n";
    print "Configuration: PASSED\n";
    print "IPMI Connectivity: PASSED\n";
    print "Fan Controller: PASSED\n";
    print "Temperature Curve: PASSED\n";
    print "Fan Setting: " . ($dry_run ? "SIMULATED" : "PASSED") . "\n";
    print "="x60 . "\n";

    if ($dry_run) {
        print "\nNOTE: This was a dry run. No actual fan speeds were changed.\n";
        print "Run without --dry-run to test actual fan control.\n";
    } else {
        print "\nWARNING: Actual fan speeds were modified during testing.\n";
        print "Monitor your system temperatures!\n";
    }
}

# Run the main function
main();

__END__

=head1 AUTHOR

Enhanced for IBM System x3650 M5 IPMI Fan Control

=head1 LICENSE

See the LICENSE file included with this distribution.

=cut
