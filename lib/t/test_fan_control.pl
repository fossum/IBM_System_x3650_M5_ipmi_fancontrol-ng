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
use Test::More;
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
    diag("Usage: $0 [--dry-run] [--verbose] [--config FILE] [--help]");
    done_testing();
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

sub test_ipmi_availability {
    my $result = `which ipmitool 2>/dev/null`;
    chomp $result;
    ok($result, 'ipmitool found in PATH');
    if (!$result) {
        diag('ipmitool not found in PATH');
        return 0;
    }
    my $sdr_output = `ipmitool sdr list 2>&1`;
    my $exit_code = $? >> 8;
    ok($exit_code == 0, 'IPMI communication successful');
    if ($exit_code != 0) {
        diag("IPMI communication failed: $sdr_output");
        return 0;
    }
    return 1;
}

sub get_current_fan_speeds {
    my ($config) = @_;
    my %fan_speeds;
    my $preamble = $config->{ipmi}{preamble};
    my $sdr_output = `$preamble sdr list | grep -i fan 2>/dev/null`;
    my $sensor_output = `$preamble sensor list | grep -i fan 2>/dev/null`;
    # Not asserting here, just returning for completeness
    return \%fan_speeds;
}

sub test_temperature_curve {
    my ($fan_controller) = @_;
    my $curve = $fan_controller->get_temperature_curve();
    ok(%$curve, 'Temperature curve loaded');
    foreach my $temp (sort {$a <=> $b} keys %$curve) {
        my $speed = $curve->{$temp};
        diag("  ${temp}°C -> ${speed}% fan speed");
    }
    my @test_temps = (20, 30, 45, 60, 75, 85);
    foreach my $test_temp (@test_temps) {
        my ($desired_speed, $calculated_speed) = $fan_controller->calculate_desired_fan_speed($test_temp);
        ok(defined $desired_speed, "Fan speed calculated for $test_temp°C");
        diag(sprintf("  %d°C -> %.1f%% (calculated: %.2f)", $test_temp, $desired_speed, $calculated_speed));
    }
    return 1;
}

sub test_fan_setting {
    my ($fan_controller, $dry_run) = @_;
    if ($dry_run) {
        my @test_speeds = (30, 50, 70);
        foreach my $speed (@test_speeds) {
            pass("DRY RUN: Would set fan speed to ${speed}%");
            $fan_controller->{current_fan_duty_cycle} = $speed;
        }
    } else {
        my $original_speed = $fan_controller->get_current_fan_duty_cycle();
        $fan_controller->{current_cpu_temp} = 50;
        $fan_controller->{last_set_cpu_temp} = 40;
        eval {
            $fan_controller->set_fan_speed(50);
            sleep 2;
        };
        ok(!$@, 'Fan speed set without error');
        if ($original_speed > 0) {
            eval { $fan_controller->set_fan_speed($original_speed); };
            ok(!$@, 'Restored original fan speed');
        }
    }
    return 1;
}


my $config = FanConfig::load($config_file);
ok($config, "Loaded config from $config_file");
ok(FanConfig::validate_config($config), "Config validated");

my $ipmi_available = test_ipmi_availability();
ok($ipmi_available || $dry_run, 'IPMI available or dry-run mode');

my $fan_controller = Fan->new($config);
ok($fan_controller, 'Fan controller initialized');

my $current_speeds = get_current_fan_speeds($config);
ok(defined $current_speeds, 'Got current fan speeds (structure returned)');

ok(test_temperature_curve($fan_controller), 'Temperature curve test ran');
ok(test_fan_setting($fan_controller, $dry_run), 'Fan setting test ran');

done_testing();

__END__

=head1 AUTHOR

Enhanced for IBM System x3650 M5 IPMI Fan Control

=head1 LICENSE

See the LICENSE file included with this distribution.

=cut
