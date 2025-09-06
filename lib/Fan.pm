#!/usr/bin/perl

=head1 NAME

Fan - Fan control utilities for IPMI fan control

=head1 SYNOPSIS

	use Fan;

	my $fan = Fan->new($config);
	$fan->set_fan_speed(50);
	$fan->update_fan_speed($cpu_temp);

=head1 DESCRIPTION

This module provides fan control utilities for the IPMI fan control script.
It handles fan speed calculations, IPMI commands, and temperature-to-speed
mapping with linear interpolation.

=head1 FUNCTIONS

=cut

package Fan;

use strict;
use warnings;
use List::Util qw[min max];

=head2 new

Creates a new Fan object with configuration settings.

=over 4

=item Parameters: $config - Configuration hash reference

=item Returns: Fan object instance

=back

=cut

sub new {
	my ($class, $config) = @_;

	my $self = {
		config => $config,
		hostname => $config->{system}{hostname},
		number_of_fanbanks => $config->{system}{number_of_fanbanks},
		min_temp_change => $config->{system}{min_temp_change},
		ipmi_preamble => $config->{ipmi}{preamble},
		current_fan_duty_cycle => 0,
		current_cpu_temp => 0,
		current_gpu_temp => 0,
		last_set_cpu_temp => 0,
		last_set_gpu_temp => 0,
		cpu_temp_to_fan_speed => {},
		cpu_temp_scale => {},
	};

	bless $self, $class;

	# Load temperature curve from config
	$self->_load_temperature_curve();
	$self->_calculate_scalars();

	return $self;
}

=head2 _load_temperature_curve

Internal method to load temperature curve from configuration.

=cut

sub _load_temperature_curve {
	my ($self) = @_;

	# Parse temperature curve from config
	foreach my $key (keys %{$self->{config}{temperature_curve}}) {
		if ($key =~ /^temp_(\d+)$/) {
			my $temp = $1;
			$self->{cpu_temp_to_fan_speed}{$temp} = $self->{config}{temperature_curve}{$key};
		}
	}
}

=head2 _internal_do_set_fan_speed

Internal method that sets the fan speed for each individual fan bank using IPMI raw commands.

=over 4

=item Parameters: $fan_speed - The desired fan speed percentage (0-100)

=back

=cut

sub _internal_do_set_fan_speed {
	my ($self, $fan_speed) = @_;

	# Sets the speed for each individual fan
	for (my $i = 1; $i <= $self->{number_of_fanbanks}; $i++) {
		print "Setting FanBank n\u00b0$i speed at $fan_speed\n";
		#ipmitool raw 0x3a 0x07 1 100 0
		`$self->{ipmi_preamble} raw 0x3a 0x07 $i $fan_speed 0x01> /dev/null 2>&1`;
	}
}

=head2 set_fan_speed

Sets the fan speed if temperature change exceeds minimum threshold.

=over 4

=item Parameters: $fan_speed - The desired fan speed percentage (0-100)

=back

=cut

sub set_fan_speed {
	my ($self, $fan_speed) = @_;

	my $cpu_temp_difference = $self->{current_cpu_temp} - $self->{last_set_cpu_temp};
	my $gpu_temp_difference = $self->{current_gpu_temp} - $self->{last_set_gpu_temp};

	if ( ( (abs $cpu_temp_difference) > $self->{min_temp_change} ) or
		 ( (abs $gpu_temp_difference) > $self->{min_temp_change} ) ) {

		# Set all fan banks to operate at $fan_speed duty cycle (0x0-0x64 valid range)
		print "\n";
		print "********************** Updating Fan Speeds **********************\n";
		print "We last updated fan speed $cpu_temp_difference *C ago (CPU Temperature).\n";
		print "We last updated fan speed $gpu_temp_difference *C ago (GPU Temperature).\n";
		print "Current CPU Temperature is $self->{current_cpu_temp} *C.\n";
		print "Current GPU Temperature is $self->{current_gpu_temp} *C.\n";
		print "*****************************************************************\n";

		$self->{last_set_cpu_temp} = $self->{current_cpu_temp};
		$self->{last_set_gpu_temp} = $self->{current_gpu_temp};
		$self->{current_fan_duty_cycle} = $fan_speed;

		$self->_internal_do_set_fan_speed($fan_speed);
	}
}

=head2 _calculate_scalars

Internal method that calculates the linear interpolation coefficients (slope and y-intercept)
for each temperature range based on the cpu_temp_to_fan_speed hash.
This creates smooth transitions between temperature points.

=cut

sub _calculate_scalars {
	my ($self) = @_;

	my @previous = ();
	foreach my $a (sort keys %{$self->{cpu_temp_to_fan_speed}}) {
		my @current = ($a, $self->{cpu_temp_to_fan_speed}{$a});

		if (@previous) {
			my $m = ($current[1] - $previous[1]) / ($current[0] - $previous[0]);
			my $b = $current[1] - ($m * $current[0]);

			$self->{cpu_temp_scale}{$a} = [($m, $b)];
		}

		@previous = @current;
	}
}

=head2 calculate_desired_fan_speed

Calculates the desired fan speed based on current CPU temperature using
linear interpolation between temperature curve points.

=over 4

=item Parameters: $current_cpu_temp - Current CPU temperature in degrees Celsius

=item Returns: Desired fan speed percentage (0-100)

=back

=cut

sub calculate_desired_fan_speed {
	my ($self, $current_cpu_temp) = @_;

	my $desired_fan_speed = 0;
	my $calculated_speed = 0;

	foreach my $a (reverse sort keys %{$self->{cpu_temp_scale}}) {
		if ($current_cpu_temp <= $a) {
			my @formula = @{$self->{cpu_temp_scale}{$a}};
			$calculated_speed = ($formula[0] * $current_cpu_temp) + $formula[1];
			$desired_fan_speed = sprintf("%.0f", $calculated_speed);
		}
	}

	return ($desired_fan_speed, $calculated_speed);
}

=head2 update_fan_speed

Main update method that calculates desired fan speeds using linear interpolation
and updates the fans accordingly. Also outputs metrics to InfluxDB format for monitoring.

=over 4

=item Parameters: $current_cpu_temp - Current CPU temperature in degrees Celsius
				  $current_gpu_temp - Current GPU temperature in degrees Celsius (optional, defaults to 0)

=back

=cut

sub update_fan_speed {
	my ($self, $current_cpu_temp, $current_gpu_temp) = @_;
	$current_gpu_temp ||= 0;

	$self->{current_cpu_temp} = $current_cpu_temp;
	$self->{current_gpu_temp} = $current_gpu_temp;

	print "Maximum CPU Temperature Seen: $current_cpu_temp degrees C.\n";
	print "Maximum GPU Temperature Seen: $current_gpu_temp degrees C.\n";

	my ($desired_fan_speed, $calculated_speed) = $self->calculate_desired_fan_speed($current_cpu_temp);

	print "Current Fan Duty Cycle: $self->{current_fan_duty_cycle}%\n";
	print "Desired Fan Duty Cycle: $desired_fan_speed%\n";

	# Output basic InfluxDB metrics to /tmp/fan_speed_telegraf
	my $speed_raw = sprintf("%x", $calculated_speed);
	open(FH, '>', '/tmp/fan_speed_telegraf') or die $!;
	print FH "fans,host=$self->{hostname} speed_percent=$calculated_speed\n";
	print FH "fans,host=$self->{hostname} speed_raw=$speed_raw\n";
	close(FH);

	$self->set_fan_speed($desired_fan_speed);
}

=head2 get_current_fan_duty_cycle

Returns the current fan duty cycle percentage.

=over 4

=item Returns: Current fan duty cycle percentage

=back

=cut

sub get_current_fan_duty_cycle {
	my ($self) = @_;
	return $self->{current_fan_duty_cycle};
}

=head2 get_temperature_curve

Returns the current temperature curve hash.

=over 4

=item Returns: Hash reference of temperature to fan speed mappings

=back

=cut

sub get_temperature_curve {
	my ($self) = @_;
	return $self->{cpu_temp_to_fan_speed};
}

1;

__END__

=head1 AUTHOR

Enhanced for IBM System x3650 M5 IPMI Fan Control

=head1 LICENSE

See the LICENSE file included with this distribution.

=cut
