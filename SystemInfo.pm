#!/usr/bin/perl

=head1 NAME

SystemInfo - System information utilities for IPMI fan control

=head1 SYNOPSIS

    use SystemInfo;

    my $cpu_count = SystemInfo::get_cpu_count();
    my $hostname = SystemInfo::get_hostname();

=head1 DESCRIPTION

This module provides system information utilities for the IPMI fan control script.
It includes functions to detect hardware configuration and system properties.

=head1 FUNCTIONS

=cut

package SystemInfo;

use strict;
use warnings;
use Exporter qw(import);

our @EXPORT_OK = qw(get_cpu_count get_system_info);
our %EXPORT_TAGS = (
    'all' => [@EXPORT_OK]
);

=head2 get_cpu_count

Detects the number of physical CPU packages in the system by parsing /proc/cpuinfo.

=over 4

=item Returns: Integer - Number of physical CPU packages

=back

=cut

sub get_cpu_count {
    my $cpu_count = 0;
    my %physical_ids;

    # Try to read /proc/cpuinfo to count physical CPUs
    if (open(my $fh, '<', '/proc/cpuinfo')) {
        while (my $line = <$fh>) {
            chomp $line;
            # Look for physical id line to count unique physical CPUs
            if ($line =~ /^physical id\s*:\s*(\d+)/) {
                $physical_ids{$1} = 1;
            }
        }
        close($fh);

        # Count unique physical IDs
        $cpu_count = scalar keys %physical_ids;

        # If no physical id found, try counting processor entries
        if ($cpu_count == 0) {
            seek($fh, 0, 0) if open($fh, '<', '/proc/cpuinfo');
            my $processor_count = 0;
            while (my $line = <$fh>) {
                chomp $line;
                if ($line =~ /^processor\s*:/) {
                    $processor_count++;
                }
            }
            close($fh);

            # Assume 2 cores per CPU if we can't determine physical layout
            $cpu_count = int(($processor_count + 1) / 2) || 1;
        }
    }

    # Fallback to 1 if detection failed
    $cpu_count = 1 if $cpu_count == 0;

    return $cpu_count;
}

=head2 get_system_info

Returns a hash reference containing various system information.

=over 4

=item Parameters: $config - Optional configuration hash reference

=item Returns: HashRef - System information including CPU count, hostname, etc.

=back

=cut

sub get_system_info {
    my ($config) = @_;

    my $hostname = 'localhost';
    if ($config && $config->{system} && $config->{system}{hostname}) {
        $hostname = $config->{system}{hostname};
    }

    return {
        cpu_count => get_cpu_count(),
        hostname  => $hostname,
        kernel    => `uname -r` =~ s/\n//gr,
        arch      => `uname -m` =~ s/\n//gr,
        config    => $config,
    };
}

1;

__END__

=head1 AUTHOR

Enhanced for IBM System x3650 M5 IPMI Fan Control

=head1 LICENSE

See the LICENSE file included with this distribution.

=cut
