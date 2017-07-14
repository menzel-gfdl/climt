from __future__ import division
from ..._core import ClimtSpectralDynamicalCore
from sympl import replace_none_with_default, DataArray
import numpy as np
import sys
try:
    from . import _gfs_dynamics
except ImportError:
    print("Import failed. GFS dynamical core will not be available!")


class GfsDynamicalCore(ClimtSpectralDynamicalCore):
    """
    Climt interface to the GFS dynamical core. The GFS
    code is available on `github`_.

    .. _github:
       https://github.com/jswhit/gfs-dycore
    """

    _climt_inputs = {
        'eastward_wind': 'm s^-1',
        'northward_wind': 'm s^-1',
        'air_temperature': 'degK',
        'surface_air_pressure': 'Pa',
        'air_pressure': 'Pa',
        'air_pressure_on_interface_levels': 'Pa',
        'specific_humidity': 'g kg^-1',
        'surface_geopotential': 'm^2 s^-2',
        'atmosphere_relative_vorticity': 's^-1',
        'divergence_of_wind': 's^-1',
        'mole_fraction_of_ozone_in_air': 'dimensionless',
        'mass_content_of_cloud_ice_in_atmosphere_layer': 'g m^-2',
        'mass_content_of_cloud_liquid_water_in_atmosphere_layer': 'g m^-2',
        'gfs_tracers': 'dimensionless',
    }

    _climt_outputs = {
        'eastward_wind': 'm s^-1',
        'northward_wind': 'm s^-1',
        'air_temperature': 'degK',
        'air_pressure': 'Pa',
        'air_pressure_on_interface_levels': 'Pa',
        'surface_air_pressure': 'Pa',
        'specific_humidity': 'g kg^-1',
        'surface_geopotential': 'm^2 s^-2',
        'atmosphere_relative_vorticity': 's^-1',
        'divergence_of_wind': 's^-1',
        'mole_fraction_of_ozone_in_air': 'dimensionless',
        'mass_content_of_cloud_ice_in_atmosphere_layer': 'g m^-2',
        'mass_content_of_cloud_liquid_water_in_atmosphere_layer': 'g m^-2',
    }

    _climt_diagnostics = {
        # 'downward_air_velocity': 'm s^-1',
    }

    extra_dimensions = {'tracer_number': np.arange(4)}

    quantity_descriptions = {
        'gfs_tracers': {
            'dims': ['x', 'y', 'mid_levels', 'tracer_number'],
            'units': 'dimensionless',
            'default_value': 0.
        }
    }

    def __init__(
            self,
            number_of_latitudes=94,
            number_of_longitudes=198,
            number_of_levels=28,
            number_of_tracers=0,
            number_of_damped_levels=0,
            dry_pressure=1.0132e5,
            time_step=1200.,
            planetary_radius=None,
            planetary_rotation_rate=None,
            universal_gas_constant=None,
            gas_constant_dry_air=None,
            gas_constant_condensible=None,
            acceleration_gravity=None,
            specific_heat_dry_air=None,
            specific_heat_condensible=None):
        """
        Initialise the GFS dynamical core.

        Args:

            number_of_latitudes (int, optional):
                The desired number of latitudes for the model. Note that
                not all combinations of latitudes and longitudes are
                acceptable. In particular, the number of latitudes must be
                :math:`\leq (longitudes)/2`.

            number_of_longitudes (int, optional):
                The desired number of longitudes. The resolution of the model in `Txx`
                notation is approximately :math:`xx = longitudes/3`. So, 192
                longitudes is T64, etc.,

            number_of_levels (int, optional):
                The desired number of levels. **Setting this option is not supported yet.**

            number_of_tracers (int, optional):
                The number of additional tracers to be used by the model. A minimum of
                four tracers are used for specific humidity, ozone and liquid and solid cloud condensate.
                This number indicates number of tracers beyond these three. These tracers
                will appear in the state dictionary in a :code:`DataArray` whose key is
                :code:`gfs_tracers` and dimensions are
                :code:`(number_of_longitudes, number_of_latitudes, number_of_levels,
                number_of_tracers)`.

            number_of_damped_levels (int, optional):
                The number of levels from the model top which are Rayleigh damped.

            dry_pressure (float, optional):
                The dry pressure decides the mass of the dry atmosphere, to be used by the
                dycore to keep the dry mass of the atmosphere constant for the duration of the run.
                The default value corresponds to :math:`10^5\ Pa`, which is suitable for the
                current atmospheric mass on earth.

            time_step (float, optional):
                The time step to be used by the model in :math:`s`.

            planetary_radius (float, optional):
                The radius of the planet to be used in :math:`m`. If None, the default
                value from :code:`sympl.default_constants` is used.

            planetary_rotation_rate (float, optional):
                The rotation rate of the planet to be used in :math:`s^{-1}`. If None, the default
                value from :code:`sympl.default_constants` is used.

            universal_gas_constant (float):
                value of the gas constant in :math:`J K^{-1} mol^{-1}`.
                Default value from climt.default_constants is used if None.

            gas_constant_dry_air (float, optional):
                The gas constant for dry air in :math:`J kg^{-1} K^{-1}`.
                If None, the default value in :code:`sympl.default_constants` is used.

            gas_constant_condensible (float, optional):
                The gas constant for the condensible substance in :math:`J kg^{-1} K^{-1}`.
                If None, the default value in :code:`sympl.default_constants` is used.

            acceleration_gravity (float):
                value of acceleration due to gravity in
                :math:`m s^{-1}`. If None, Default value from :code:`sympl.default_constants` is
                used.

           specific_heat_dry_air (float, optional):
                The heat capacity of dry air in :math:`J kg^{-1} K^{-1}`.
                If None, the default value in :code:`sympl.default_constants` is used.

            specific_heat_condensible (float, optional):
                The heat capacity of the condensible substance in :math:`J kg^{-1} K^{-1}`.
                If None, the default value in :code:`sympl.default_constants` is used.



        """
        if specific_heat_condensible is not None:
            specific_heat_condensible = DataArray(
                specific_heat_condensible, attrs={'units': 'J kg^-1 K^-1'})

        self._time_step = float(time_step)

        self._radius = replace_none_with_default(
            'planetary_radius', planetary_radius)

        self._omega = replace_none_with_default(
            'planetary_rotation_rate', planetary_rotation_rate)

        self._R = replace_none_with_default(
            'universal_gas_constant', universal_gas_constant)

        self._Rd = replace_none_with_default(
            'gas_constant_of_dry_air', gas_constant_dry_air)

        self._Rv = replace_none_with_default(
            'gas_constant_of_water_vapor', gas_constant_condensible)

        self._g = replace_none_with_default(
            'gravitational_acceleration', acceleration_gravity)

        self._Cp = replace_none_with_default(
            'heat_capacity_of_dry_air_at_constant_pressure',
            specific_heat_dry_air)

        self._Cvap = replace_none_with_default(
            'heat_capacity_of_water_vapor_at_constant_pressure',
            specific_heat_condensible)

        self._fvirt = (1 - self._Rd/self._Rv)/(self._Rd/self._Rv)

        # Sanity Checks
        assert number_of_tracers >= 0
        assert number_of_levels > 0
        assert number_of_latitudes > 0
        assert number_of_longitudes > 0
        assert number_of_damped_levels >= 0

        self._num_lats = number_of_latitudes

        self._num_lons = number_of_longitudes

        self._num_levs = number_of_levels

        self._damping_levels = number_of_damped_levels

        # 4 tracers at least for water vapour, ozone and liquid and solid cloud condensate
        self._num_tracers = number_of_tracers + 4
        self.extra_dimensions['tracer_number'] = np.arange(self._num_tracers)

        self._dry_pressure = dry_pressure

        # Cannot set to new value currently.
        if self._num_levs != 28:
            raise NotImplementedError(
                'Setting levels is not supported yet!.')

        self._truncation = int(self._num_lons/3 - 2)

        self._spectral_dim = int(
            (self._truncation + 1)*(self._truncation + 2)/2)

        _gfs_dynamics.set_time_step(self._time_step)

        _gfs_dynamics.set_constants(self._radius, self._omega,
                                    self._R, self._Rd, self._Rv,
                                    self._g, self._Cp, self._Cvap)

        _gfs_dynamics.set_model_grid(self._num_lats,
                                     self._num_lons,
                                     self._num_levs,
                                     self._truncation,
                                     self._spectral_dim,
                                     self._num_tracers)

        print('Initialising dynamical core, this could take some time...')

        latitudes, longitudes, sigma, sigma_interface = _gfs_dynamics.init_model(self._dry_pressure,
                                                                                 self._damping_levels)

        print('Done!')

        latitude = dict(label='latitude',
                        values=np.degrees(latitudes[0, :]),
                        units='degrees_north')

        longitude = dict(label='longitude',
                         values=np.degrees(longitudes[:, 0]),
                         units='degrees_east')

        sigma_levels = dict(label='sigma_levels',
                            values=sigma,
                            units='dimensionless')

        sigma_int_levels = dict(label='sigma_interface_levels',
                                values=sigma_interface,
                                units='dimensionless')

        self.grid_definition = dict(y=latitude, x=longitude,
                                    z=sigma_levels,
                                    interface_levels=sigma_int_levels)

        # Random array to slice variables
        self.initialise_state_signature()

    def __call__(self, state):
        """ Step the dynamical core by one step

        Args:
            state (dict): The state dictionary.

        Returns:
            diagnostics, new_state (dict):
                The new state and associated diagnostics.
        """

        raw_input_arrays = self.get_numpy_arrays_from_state('_climt_inputs', state)

        output_dict = self.create_state_dict_for('_climt_outputs', state)

        update_spectral_arrays = False
        if self.state_is_modified_externally(raw_input_arrays):
            update_spectral_arrays = True

        lnsp = np.log(raw_input_arrays['surface_air_pressure'])
        t_virt = raw_input_arrays['air_temperature']*(
            1 + self._fvirt.values.item()*raw_input_arrays['specific_humidity'])

        raw_input_arrays['gfs_tracers'][:, :, :, 0] = raw_input_arrays['specific_humidity']
        raw_input_arrays['gfs_tracers'][:, :, :, 1] = \
            raw_input_arrays['mole_fraction_of_ozone_in_air']
        raw_input_arrays['gfs_tracers'][:, :, :, 2] = \
            raw_input_arrays['mass_content_of_cloud_liquid_water_in_atmosphere_layer']
        raw_input_arrays['gfs_tracers'][:, :, :, 3] = \
            raw_input_arrays['mass_content_of_cloud_ice_in_atmosphere_layer']

        _gfs_dynamics.assign_grid_arrays(
            raw_input_arrays['eastward_wind'],
            raw_input_arrays['northward_wind'],
            t_virt,
            lnsp,
            raw_input_arrays['gfs_tracers'],
            raw_input_arrays['atmosphere_relative_vorticity'],
            raw_input_arrays['divergence_of_wind'])

        _gfs_dynamics.assign_pressure_arrays(
            raw_input_arrays['surface_air_pressure'],
            raw_input_arrays['air_pressure'],
            raw_input_arrays['air_pressure_on_interface_levels'])

        _gfs_dynamics.set_topography(raw_input_arrays['surface_geopotential'])

        tendencies = {}
        if self.prognostics:
            tendencies, diagnostics = self.prognostics(state)

        temp_tend, q_tend, u_tend, v_tend, ps_tend, tracer_tend = \
            return_tendency_arrays_or_zeros(['air_temperature',
                                             'specific_humidity',
                                             'eastward_wind',
                                             'northward_wind',
                                             'surface_air_pressure',
                                             'gfs_tracers'],
                                            raw_input_arrays, tendencies)

        # see Pg. 12 in gfsModelDoc.pdf
        virtual_temp_tend = temp_tend*(
            1 + self._fvirt.values.item()*raw_input_arrays['specific_humidity']) + \
            self._fvirt.values.item()*t_virt*q_tend

        # dlnps/dt = (1/ps)*dps/dt
        lnps_tend = (1. / raw_input_arrays['surface_air_pressure'])*ps_tend

        _gfs_dynamics.assign_tendencies(u_tend, v_tend, virtual_temp_tend,
                                        lnps_tend, tracer_tend)

        if update_spectral_arrays:
            _gfs_dynamics.update_spectral_arrays()

        _gfs_dynamics.take_one_step()
        _gfs_dynamics.convert_to_grid()
        _gfs_dynamics.calculate_pressure()

        raw_input_arrays['air_temperature'][:] = t_virt/(
            1 + self._fvirt.values.item()*raw_input_arrays['specific_humidity'])

        self.store_current_state_signature(raw_input_arrays)

        for quantity in self._climt_outputs.keys():
                output_dict[quantity].values[:] = raw_input_arrays[quantity]

        return {}, output_dict

    def initialise_state_signature(self):

        self._random_slice_x = np.random.randint(0, self._num_lons, size=(10, 10, 10))
        self._random_slice_y = np.random.randint(0, self._num_lats, size=(10, 10, 10))
        self._random_slice_z = np.random.randint(0, self._num_levs, size=(10, 10, 10))

        self._hash_u = 1000
        self._hash_v = 1000
        self._hash_temp = 1000
        self._hash_press = 1000
        self._hash_surf_press = 1000

    def calculate_state_signature(self, state_arr):
        """ Calculates hash signatures from state """
        random_u = state_arr['eastward_wind'][self._random_slice_x, self._random_slice_y,
                                              self._random_slice_z]

        if sys.version_info > (3, 0):
            hash_u = hash(random_u.data.tobytes())
        else:
            random_u.flags.writeable = False
            hash_u = hash(random_u.data)

        random_v = state_arr['northward_wind'][self._random_slice_x, self._random_slice_y,
                                               self._random_slice_z]
        if sys.version_info > (3, 0):
            hash_v = hash(random_v.data.tobytes())
        else:
            random_v.flags.writeable = False
            hash_v = hash(random_v.data)

        random_temp = state_arr['air_temperature'][self._random_slice_x, self._random_slice_y,
                                                   self._random_slice_z]
        if sys.version_info > (3, 0):
            hash_temp = hash(random_temp.data.tobytes())
        else:
            random_temp.flags.writeable = False
            hash_temp = hash(random_temp.data)

        random_pressure = state_arr['air_pressure'][self._random_slice_x, self._random_slice_y,
                                                    self._random_slice_z]
        if sys.version_info > (3, 0):
            hash_press = hash(random_pressure.data.tobytes())
        else:
            random_pressure.flags.writeable = False
            hash_press = hash(random_pressure.data)

        random_ps = state_arr['surface_air_pressure'][self._random_slice_x, self._random_slice_y]

        if sys.version_info > (3, 0):
            hash_ps = hash(random_ps.data.tobytes())
        else:
            random_ps.flags.writeable = False
            hash_ps = hash(random_ps.data)

        return hash_u, hash_v, hash_temp, hash_press, hash_ps

    def state_is_modified_externally(self, state_arr):
        """ Function to check if grid space arrays have been modified outside the dynamical core """

        hash_u, hash_v, hash_temp, hash_press, hash_ps = self.calculate_state_signature(state_arr)

        if (
            (hash_u != self._hash_u) or
            (hash_v != self._hash_v) or
            (hash_press != self._hash_press) or
            (hash_ps != self._hash_surf_press) or
           (hash_temp != self._hash_temp)):
                print('State modified, setting spectral arrays')
                self._hash_u = hash_u
                self._hash_v = hash_v
                self._hash_temp = hash_temp
                self._hash_surf_press = hash_ps
                self._hash_press = hash_press
                return True
        else:
            return False

    def store_current_state_signature(self, output_arr):
        """ Store state signature for comparison during next time step """

        hash_u, hash_v, hash_temp, hash_press, hash_ps = self.calculate_state_signature(output_arr)

        self._hash_u = hash_u
        self._hash_v = hash_v
        self._hash_temp = hash_temp
        self._hash_surf_press = hash_ps
        self._hash_press = hash_press


def return_tendency_arrays_or_zeros(quantity_list, state, tendencies):

    tendency_list = []
    for quantity in quantity_list:
        if quantity in tendencies.keys():
            tendency_list.append(np.asfortranarray(tendencies[quantity].values))
        elif quantity in state.keys():
            tendency_list.append(np.zeros(state[quantity].shape, order='F'))
        else:
            raise IndexError("{} not found in input state or tendencies".format(quantity))

    return tendency_list