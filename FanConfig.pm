#!/usr/bin/perl

=head1 NAME

FanConfig - Configuration file utilities for IPMI fan control

=head1 SYNOPSIS

    use FanConfig;

    my $config = FanConfig::load('./config.conf');
    my $hostname = FanConfig::get_value($config, 'system', 'hostname');

=head1 DESCRIPTION

This module provides configuration file loading and parsing utilities for the
IPMI fan control script. It handles INI-style configuration files with sections
and key-value pairs.

=head1 FUNCTIONS

=cut

package FanConfig;

use strict;
use warnings;
use Exporter qw(import);

our @EXPORT_OK = qw(load get_value get_section validate_config);
our %EXPORT_TAGS = (
    'all' => [@EXPORT_OK]
);

=head2 load

Loads configuration from an INI-style configuration file and returns a hash
reference with all configuration values organized by sections.

=over 4

=item Parameters: $config_file - Path to configuration file (optional, defaults to './config.conf')

=item Returns: HashRef - Configuration hash with all settings organized by section

=back

=cut

sub load {
    my ($config_file) = @_;
    $config_file ||= './config.conf';

    my %config = ();
    my $current_section = '';

    if (open(my $fh, '<', $config_file)) {
        while (my $line = <$fh>) {
            chomp $line;
            $line =~ s/^\s+|\s+$//g;  # Trim whitespace

            # Skip empty lines and comments
            next if $line =~ /^$/ || $line =~ /^#/;

            # Handle sections [section_name]
            if ($line =~ /^\[(.+)\]$/) {
                $current_section = $1;
                next;
            }

            # Handle key = value pairs
            if ($line =~ /^([^=]+)\s*=\s*(.*)$/) {
                my ($key, $value) = ($1, $2);
                $key =~ s/^\s+|\s+$//g;    # Trim key
                $value =~ s/^\s+|\s+$//g;  # Trim value

                if ($current_section) {
                    $config{$current_section}{$key} = $value;
                } else {
                    $config{$key} = $value;
                }
            }
        }
        close($fh);
    } else {
        warn "Warning: Could not open config file '$config_file': $!";
        # Return default configuration
        %config = _get_default_config();
    }

    return \%config;
}

=head2 _get_default_config

Internal function that returns default configuration values when config file
cannot be loaded.

=over 4

=item Returns: Hash - Default configuration values

=back

=cut

sub _get_default_config {
    return (
        system => {
            hostname => 'localhost',
            number_of_fans => 6,
            number_of_fanbanks => 2,
            min_temp_change => 0,
            seconds_to_sleep => 3,
        },
        ipmi => {
            preamble => 'ipmitool',
            cmd_listall => 'sdr list full',
        },
        temperature_curve => {
            temp_80 => 250,
            temp_70 => 150,
            temp_55 => 50,
            temp_40 => 25,
            temp_10 => 5,
        }
    );
}

=head2 get_value

Gets a specific configuration value from the config hash.

=over 4

=item Parameters: $config - Configuration hash reference
                  $section - Section name
                  $key - Key name
                  $default - Default value if key not found (optional)

=item Returns: The configuration value or default

=back

=cut

sub get_value {
    my ($config, $section, $key, $default) = @_;

    if (defined $config->{$section} && defined $config->{$section}{$key}) {
        return $config->{$section}{$key};
    }

    return $default;
}

=head2 get_section

Gets an entire configuration section as a hash reference.

=over 4

=item Parameters: $config - Configuration hash reference
                  $section - Section name

=item Returns: HashRef - The section hash or empty hash if not found

=back

=cut

sub get_section {
    my ($config, $section) = @_;

    return $config->{$section} || {};
}

=head2 validate_config

Validates that required configuration sections and keys are present.

=over 4

=item Parameters: $config - Configuration hash reference

=item Returns: Boolean - True if valid, false otherwise

=back

=cut

sub validate_config {
    my ($config) = @_;

    # Required sections
    my @required_sections = qw(system ipmi temperature_curve);

    # Required keys per section
    my %required_keys = (
        system => [qw(hostname number_of_fanbanks)],
        ipmi => [qw(preamble)],
        temperature_curve => [],  # At least one temp_XX entry required
    );

    # Check required sections exist
    foreach my $section (@required_sections) {
        if (!exists $config->{$section}) {
            warn "Missing required configuration section: [$section]";
            return 0;
        }
    }

    # Check required keys within sections
    foreach my $section (keys %required_keys) {
        foreach my $key (@{$required_keys{$section}}) {
            if (!exists $config->{$section}{$key}) {
                warn "Missing required configuration key: $key in section [$section]";
                return 0;
            }
        }
    }

    # Check temperature curve has at least one entry
    my $temp_count = 0;
    foreach my $key (keys %{$config->{temperature_curve}}) {
        if ($key =~ /^temp_\d+$/) {
            $temp_count++;
        }
    }

    if ($temp_count == 0) {
        warn "No temperature curve entries found (temp_XX = value)";
        return 0;
    }

    return 1;
}

1;

__END__

=head1 AUTHOR

Enhanced for IBM System x3650 M5 IPMI Fan Control

=head1 LICENSE

See the LICENSE file included with this distribution.

=cut
