import pandas as pd
import os
import glob
from xlrd import XLRDError
import pyomo.core as pyomo
from .features.modelhelper import *
from .identify import *
import math
import numpy as np


def read_input(input_files, year):
    """Read Excel input file and prepare URBS input dict.

    Reads the Excel spreadsheets that adheres to the structure shown in
    mimo-example.xlsx. Column titles in 'Demand' and 'SupIm' are split, so that
    'Site.Commodity' becomes the MultiIndex column ('Site', 'Commodity').

    Args:
        - filename: filename to Excel spreadsheets
        - year: current year for non-intertemporal problems

    Returns:
        a dict of up to 12 DataFrames
    """

    if os.path.isdir(input_files):
        glob_input = os.path.join(input_files, '*.xlsx')
        input_files = sorted(glob.glob(glob_input))
    else:
        input_files = [input_files]

    gl = []
    sit = []
    com = []
    pro = []
    pro_com = []
    tra = []
    sto = []
    valo = []
    dem = []
    sup = []
    bsp = []
    ds = []
    ef = []

    for filename in input_files:
        with pd.ExcelFile(filename) as xls:

            global_prop = xls.parse('Global').set_index(['Property'])
            # create support timeframe index
            if ('Support timeframe' in
                    xls.parse('Global').set_index('Property').value):
                support_timeframe = (
                    global_prop.loc['Support timeframe']['value'])
                global_prop = (
                    global_prop.drop(['Support timeframe'])
                    .drop(['description'], axis=1))
            else:
                support_timeframe = year

            # create MILP index
            if not global_prop.filter(like='MILP', axis=0).empty:
                milp = global_prop.filter(like='MILP', axis=0).drop(['description'], axis=1)
                global_prop = (global_prop.drop(milp.index))
                milp = milp[milp.values == 'yes']

            global_prop = pd.concat([global_prop], keys=[support_timeframe],
                                    names=['support_timeframe'])
            gl.append(global_prop)
            site = xls.parse('Site').set_index(['Name'])
            site = pd.concat([site], keys=[support_timeframe],
                             names=['support_timeframe'])
            sit.append(site)
            commodity = (
                xls.parse('Commodity')
                   .set_index(['Site', 'Commodity', 'Type']))
            commodity = pd.concat([commodity], keys=[support_timeframe],
                                  names=['support_timeframe'])
            com.append(commodity)
            process = xls.parse('Process').set_index(['Site', 'Process'])
            process = pd.concat([process], keys=[support_timeframe],
                                names=['support_timeframe'])
            pro.append(process)
            process_commodity = (
                xls.parse('Process-Commodity')
                   .set_index(['Process', 'Commodity', 'Direction']))
            process_commodity = pd.concat([process_commodity],
                                          keys=[support_timeframe],
                                          names=['support_timeframe'])
            pro_com.append(process_commodity)
            demand = xls.parse('Demand').set_index(['t'])
            demand = pd.concat([demand], keys=[support_timeframe],
                               names=['support_timeframe'])
            typeday = demand.loc[:, ['weight_typeday']]
            demand = demand.drop(columns=['weight_typeday'])
            # split columns by dots '.', so that 'DE.Elec' becomes
            # the two-level column index ('DE', 'Elec')
            demand.columns = split_columns(demand.columns, '.')
            dem.append(demand)
            supim = xls.parse('SupIm').set_index(['t'])
            supim = pd.concat([supim], keys=[support_timeframe],
                              names=['support_timeframe'])
            supim.columns = split_columns(supim.columns, '.')
            sup.append(supim)

            # collect data for the additional features
            # Transmission, Storage, valo, DSM
            if 'Transmission' in xls.sheet_names:
                transmission = (
                    xls.parse('Transmission')
                    .set_index(['Site In', 'Site Out',
                                'Transmission', 'Commodity']))
                transmission = (
                    pd.concat([transmission], keys=[support_timeframe],
                              names=['support_timeframe']))
            else:
                transmission = pd.DataFrame()
            tra.append(transmission)
            if 'Storage' in xls.sheet_names:
                storage = (
                    xls.parse('Storage')
                    .set_index(['Site', 'Storage', 'Commodity']))
                storage = pd.concat([storage], keys=[support_timeframe],
                                    names=['support_timeframe'])
            else:
                storage = pd.DataFrame()
            sto.append(storage)
            if 'Variable Load' in xls.sheet_names:
                variableload = (
                    xls.parse('Variable Load')
                    .set_index(['Site', 'valo', 'Commodity']))
                variableload = pd.concat([variableload], keys=[support_timeframe],
                                    names=['support_timeframe'])
            else:
                variableload = pd.DataFrame()
            valo.append(variableload)
            if 'DSM' in xls.sheet_names:
                dsm = xls.parse('DSM').set_index(['Site', 'Commodity'])
                dsm = pd.concat([dsm], keys=[support_timeframe],
                                names=['support_timeframe'])
            else:
                dsm = pd.DataFrame()
            ds.append(dsm)
            if 'Buy-Sell-Price'in xls.sheet_names:
                buy_sell_price = xls.parse('Buy-Sell-Price').set_index(['t'])
                buy_sell_price = pd.concat([buy_sell_price],
                                           keys=[support_timeframe],
                                           names=['support_timeframe'])
                buy_sell_price.columns = \
                    split_columns(buy_sell_price.columns, '.')
            else:
                buy_sell_price = pd.DataFrame()
            bsp.append(buy_sell_price)
            if 'TimeVarEff' in xls.sheet_names:
                eff_factor = (xls.parse('TimeVarEff').set_index(['t']))
                eff_factor = pd.concat([eff_factor], keys=[support_timeframe],
                                       names=['support_timeframe'])
                eff_factor.columns = split_columns(eff_factor.columns, '.')
            else:
                eff_factor = pd.DataFrame()
            ef.append(eff_factor)

    # prepare input data
    try:
        global_prop = pd.concat(gl, sort=False)
        site = pd.concat(sit, sort=False)
        commodity = pd.concat(com, sort=False)
        process = pd.concat(pro, sort=False)
        process_commodity = pd.concat(pro_com, sort=False)
        demand = pd.concat(dem, sort=False)
        supim = pd.concat(sup, sort=False)
        transmission = pd.concat(tra, sort=False)
        storage = pd.concat(sto, sort=False)
        variableload = pd.concat(valo, sort=False)
        dsm = pd.concat(ds, sort=False)
        buy_sell_price = pd.concat(bsp, sort=False)
        eff_factor = pd.concat(ef, sort=False)
    except KeyError:
        pass

    data = {
        'global_prop': global_prop,
        'MILP': milp,
        'site': site,
        'commodity': commodity,
        'process': process,
        'process_commodity': process_commodity,
        'type day': typeday,
        'demand': demand,
        'supim': supim,
        'transmission': transmission,
        'storage': storage,
        'valo': variableload,
        'dsm': dsm,
        'buy_sell_price': buy_sell_price.dropna(axis=1, how='all'),
        'eff_factor': eff_factor.dropna(axis=1, how='all')
    }

    # sort nested indexes to make direct assignments work
    for key in data:
        if isinstance(data[key].index, pd.core.index.MultiIndex):
            data[key].sort_index(inplace=True)
    return data


# Reads in the input data for the valos. In the folder "Input Variable Load" there is a folder for each site
# containing the files for the corresponding valos at that site.
def read_in_valo_availability_data(m, timesteps, dt):
    input_dir = "Input Variable Load"
    site_dirs = [d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))]
    # Remaining valos is introduced to check that there is an operation plan for each valo in the input file.
    remaining_valos = tuple(m.valo_dict["capacity"].keys())
    m.valo_operation_plan_dict = {}

    for site_dir in site_dirs:
        site_input_dir = os.path.join(input_dir, site_dir)
        input_files = os.listdir(site_input_dir)

        for file_name in input_files:
            file_path = os.path.join(site_input_dir, file_name)
            op_plan = pd.read_csv(file_path, sep=";", index_col=0)
            if len(op_plan) < timesteps.stop:
                raise ValueError(
                    "The input file '{}', '{}' is too short. It should have at least {} timesteps.".format(site_dir,
                                                                                                           file_name,
                                                                                                           timesteps))
            else:
                op_plan = op_plan.iloc[:timesteps.stop]

            op_plan['Set Energy Content'] = op_plan['Set Energy Content'].replace(',', '.', regex=True)
            op_plan['Set Energy Content'] = pd.to_numeric(op_plan['Set Energy Content'], errors='coerce')
            op_plan['Energy Content Goal'] = op_plan['Energy Content Goal'].replace(',', '.', regex=True)
            op_plan['Energy Content Goal'] = pd.to_numeric(op_plan['Energy Content Goal'], errors='coerce')

            file_name = os.path.splitext(file_name)[0]
            site_name = os.path.splitext(site_dir)[0]
            keytuple = tuple(m.valo_dict["capacity"].keys())
            valo_tuple = [tpl for tpl in keytuple if tpl[1] == site_name and tpl[2] == file_name]
            if len(valo_tuple) == 1:
                valo = valo_tuple[0]
                validate_valo_input_files(m, dt, site_name, file_name, op_plan, valo)
                m = add_valo_fix_part_to_demand(m, dt, op_plan, valo)
                remaining_valos = [t for t in remaining_valos if t != valo]
            else:
                raise ValueError("There is no master data in the input file for the variable load '{}',"
                                 "'{}' ".format(site_name, file_name))

            operation_plan = op_plan[(op_plan['State'] == 2) | (op_plan['State'] == 3)].copy()
            operation_plan = operation_plan.reindex(op_plan.index)
            # Replace State 2 "Operate with goal" and State 3 "Operate with Sun" with 1 for binary calculation.
            # State 2 and 3 are basically the same only that there is always a 'Energy Content Goal' given for State 2.
            operation_plan['State'].replace({2: 1, 3: 1}, inplace=True)
            operation_plan['State'].fillna(0, inplace=True)
            # Add binary column 'Reset Energy Content' to allow implementation of non-vehicles where 'Set Energy
            # Content' values can be given at any time during operation.
            operation_plan['Reset Energy Content'] = np.where(
                (~operation_plan['Set Energy Content'].isna()) | (operation_plan['State'] == 0), 1, 0)

            # Extract Energy Content Goals
            production_goals = {}
            for timestep in op_plan.index:
                energy_content_goal= op_plan.loc[timestep, 'Energy Content Goal']
                if pd.notna(energy_content_goal):
                    production_goals[timestep] = energy_content_goal
            site_valo_key = (site_name, file_name)

            m.valo_operation_plan_dict[site_valo_key] = {
                'set_energy_content': operation_plan['Set Energy Content'],
                'production_goals': production_goals,
                'state': operation_plan['State'],
                'reset': operation_plan['Reset Energy Content']
            }
    if len(remaining_valos) != 0:
        raise ValueError("There is no operation plan for the variable loads '{}' introduced in the input "
                         "file".format(remaining_valos))
    return m


def validate_valo_input_files(m, dt, site_name, file_name, op_plan, valo):
    # Ensure State only contains 0,1,2,3:
    unique_states = op_plan['State'].unique()
    allowed_values = {0, 1, 2, 3}
    invalid_values = set(unique_states) - allowed_values
    if invalid_values:
        invalid_indices = op_plan[op_plan['State'].isin(invalid_values)].index.tolist()
        raise ValueError("The 'State' column in '{}', '{}' contains the invalid"
                         " values: {} at indicenoons {}".format(site_name, file_name, invalid_values, invalid_indices))
    # Ensure that the initial State is 0
    if op_plan['State'][0] != 0:
        raise ValueError("The first value in the  'State' column in '{}', '{}' should be zero.".format(site_name, file_name))

    # Ensure that the first "Set Energy Content" value is bigger not negative
    first_set_energy_content_value = op_plan['Set Energy Content'].dropna().iloc[0]
    if first_set_energy_content_value <= 0:
        raise ValueError(
            "The first value in the 'Set Energy Content' column of '{}', '{}' should be greater than 0."
            .format(site_name, file_name))
    # Ensure -1 < set energy content < 1
    set_energy_content_values = op_plan['Set Energy Content'][pd.notna(op_plan['Set Energy Content'])]
    if not ((set_energy_content_values >= -1) & (set_energy_content_values <= 1)).all():
        raise ValueError(
            "All values in the 'Set Energy Content' column of '{}', '{}' should be between -1 and"
            " 1.".format(site_name, file_name))

    # Ensure 0 < Energy Content Goal < 1
    energy_content_goal_values = op_plan['Energy Content Goal'][pd.notna(op_plan['Energy Content Goal'])]
    if not ((energy_content_goal_values > 0) & (energy_content_goal_values <= 1)).all():
        raise ValueError(
            "All values in the 'Energy Content Goal' column of '{}', '{}' should be between 0 and "
            "1.".format(site_name, file_name))

    # Ensure that 'Energy Content Goal' is bigger than the last 'Set Energy Content'
    op_plan['Last_Energy_Start'] = op_plan['Set Energy Content'].ffill()
    mask = (op_plan['Energy Content Goal'] <= op_plan['Last_Energy_Start']) & ~op_plan['Energy Content Goal'].isna()
    if mask.any():
        invalid_indices = op_plan[mask].index.tolist()
        raise ValueError(
            "In '{}', '{}', the 'Energy Content Goal' value  at timesteps {} is not greater than the last given 'Energy"
            " Start' value.".format(site_name, file_name, invalid_indices))
    op_plan.drop(columns=['Last_Energy_Start'], inplace=True)

    # Ensure that there is no 'Set Energy Content' and 'Energy Content Goal' value given for the same timestep
    invalid_indices = op_plan[op_plan['Set Energy Content'].notna() & op_plan['Energy Content Goal'].notna()].index
    if not invalid_indices.empty:
        raise ValueError(
            "In '{}', there should not be a 'Set Energy Content' and a 'Energy Content Goal' value given for the same "
            "timestep {}.".format(file_name, invalid_indices[0]))

    # Ensure that there are only allowed transitions occuring
    '''
    The allowed state transitions are:
                               VEHICLE           VEHICLE               Non-VEHICLE              Non-VEHICLE
    State(t)   State(t+1)    Energy Goal(t)     Set Energy (t+1)       Set Energy (t)         Energy Goal (t+1)
    ------------------------------------------------------------------------------------------------------------
    0               0           no             no                          no                         no
    0               1           no             yes                        no                         yes
    0               2           no             yes                        no                         yes
    0               3           no             yes                        no                         yes
    1               0           no             no                          no                         no
    1               1           no             no                          no                         can
    1               2           no             calc                       no                         can, otherwise calc
    1               3           no             calc                       no                         can, otherwise calc
    2               0           yes            no                          yes                        no
    2               1           illegal       illegal                     yes                        yes
    2               2           can            no                          can                        can
    2               3           yes         energy goal (t)                 yes          can, otherwise energy goal (t)
    3               0           no             no                          no                         no
    3               1           illegal       illegal                     no                         yes
    3               2           illegal       illegal                     no                         yes
    3               3           no             no                          no                         can
    '''
    # 'Set Energy Content' Calculations for (1,2) and (1,3) are conducted in the fix demand calculation
    transitions = []
    for ts in range(len(op_plan) - 1):
        current_state = op_plan['State'].iloc[ts]
        next_state = op_plan['State'].iloc[ts + 1]
        transitions.append((ts, current_state, next_state))
    for ts, first_state, second_state in transitions:
        #### Energy Content Goal ####
        # Ensure that there is no 'Energy Content Goal' value given for the first timestep
        if ts == 0 or ts == 1:
            if pd.notna(op_plan.loc[ts, 'Energy Content Goal']):
                raise ValueError(
                    "There should not be any 'Energy Content Goal' value given for timesteps '0' and '1' in '{}',"
                    " '{}'".format(site_name, file_name))
        # Ensure that there is a "Energy Content Goal" value set where the state is 2 and the next state is not 2.
        if first_state == 2 and second_state != 2:
            if pd.isna(op_plan.loc[ts, 'Energy Content Goal']):
                raise ValueError(
                    "In '{}', '{}' there is no 'Energy Content Goal' value set at index {} where there's a transition "
                    "from state 2.".format(site_name, file_name, ts))
        # Ensure that there is only a "Energy Content Goal" value if the State is 2
        if first_state != 2:
            if pd.notna(op_plan.loc[ts, 'Energy Content Goal']):
                raise ValueError(
                    "A 'Energy Content Goal' value can only be set for state 2 'operate with goal' "
                    "(Found in '{}', '{}' at index {}).".format(site_name, file_name, ts))
        #### Set Energy Content ####
        # Ensure that there is no 'Set Energy Content' value given for the first timestep
        if ts == 0:
            if pd.notna(op_plan.loc[ts, 'Set Energy Content']):
                raise ValueError(
                    "There should not be any 'Set Energy Content' value given for timestep '0' in '{}', '{}'".format(
                        site_name, file_name))
        ## NO_Vehicle ##
        # If the valo is not a vehicle, there are less restrictions:
        if m.valo_dict['is-vehicle'][valo] == 0:
            # Ensure that there is no "Set Energy Content" Value given if there is a to-zero state transition.
            if second_state == 0:
                if pd.notna(op_plan.loc[ts + 1, 'Set Energy Content']):
                    raise ValueError(
                        "In '{}', '{}' there should be no 'Set Energy Content' value set for the transition from state"
                        " {} to state {} at index {}.".format(site_name, file_name, first_state, second_state, ts + 1))

            # Ensure that there is a "Set Energy Content" Value given for required transitions. For non-vehicle
            # variable loads a new "Set Energy Content" Value can always be given as long as the state is not 0.
            # Exclusion for Vehicles is checked later.
            elif (first_state, second_state) in [(0, 1), (0, 2), (0, 3), (2, 1), (3, 1), (3, 2)]:
                if pd.isna(op_plan.loc[ts + 1, 'Set Energy Content']):
                    raise ValueError(
                        "In '{}', '{}' there is no 'Set Energy Content' value set at index {} where there's a "
                        "transition from state {} to state {}.".format(site_name, file_name, ts + 1, first_state,
                                                                       second_state))

            # Ensure that if there is no "Set Energy Content" given for transition 2-3 that the "Energy Content Goal"
            # of 2 is taken.
            elif (first_state, second_state) in [(2, 3)]:
                if pd.isna(op_plan.loc[ts + 1, 'Set Energy Content']):
                    op_plan.loc[ts + 1, 'Set Energy Content'] = op_plan.loc[ts, 'Energy Content Goal']
        ## Vehicle ##
        # If the valo is a vehicle, there are aggravated restrictions:
        elif m.valo_dict['is-vehicle'][valo] == 1:
            # If the valo is a vehicle, transitions 2-1, 3-1, and 3-2 are logically impossible.
            if (first_state, second_state) in [(2, 1), (3, 1), (3, 2)]:
                raise ValueError("In '{}', '{}', there is an illegal state transition at index {} from state'{}' to "
                                 "state '{}'. Since the valo is defined as a vehicle (set in the input file) these "
                                 "transitions are illegal.".format(site_name, file_name, ts, first_state, second_state))
            # Ensure that there is no "Set Energy Content" Value given for not allowed transitions.
            if (first_state, second_state) not in [(0, 1), (0, 2), (0, 3)]:
                if pd.notna(op_plan.loc[ts + 1, 'Set Energy Content']):
                    raise ValueError(
                        "In '{}', '{}' of type 'is-vehicle' = {} there should be no 'Set Energy Content' value set for"
                        " the transition from state {} to state {} at index {}.".format(site_name, file_name,
                                                                                        m.valo_dict['is-vehicle'][valo],
                                                                                        first_state, second_state,
                                                                                        ts + 1))
            else:
                if pd.isna(op_plan.loc[ts + 1, 'Set Energy Content']):
                    raise ValueError(
                        "In '{}', '{}' there is no 'Set Energy Content' value set at index {} where there's a"
                        " transition from state {} to state {}.".format(site_name, file_name, ts + 1, first_state,
                                                                        second_state))
            if (first_state, second_state) in [(2, 3)]:
                op_plan.loc[ts + 1, 'Set Energy Content'] = op_plan.loc[ts, 'Energy Content Goal']
        else:
            raise ValueError(
                "In the Input file 'is-vehicle' has to be 0 or 1 for  '{}', '{}'.".format(site_name, file_name))

    # Ensure that the operation plan is physically feasible.
    # 'max_content' column denotes the maximum physically possible energy content. For all active states the max
    # content, if the valo operates at full power continuously, is calculated. After the calculation it is checked if
    # any Energy Content Goal value is set to be bigger than the maximum physically possible one.
    op_plan['max_content'] = np.nan
    op_plan.at[0, 'max_content'] = 0
    for t in range(1, len(op_plan)):
        if pd.isna(op_plan.at[t, 'Set Energy Content']):
            active = 1 if op_plan.at[t, 'State'] > 0 else 0
            op_plan.at[t, 'max_content'] = op_plan.at[t-1, 'max_content'] + \
                                             ((m.valo_dict['max-p'][valo] * dt * m.valo_dict['eff'][valo]) /
                                              m.valo_dict['capacity'][valo]) * active
        elif op_plan.at[t, 'Set Energy Content'] > 0:
            op_plan.at[t, 'max_content'] = op_plan.at[t, 'Set Energy Content'] + ((m.valo_dict['max-p'][valo] *
                                                                                dt * m.valo_dict['eff'][valo]) /
                                                                                m.valo_dict['capacity'][valo])
        elif op_plan.at[t, 'Set Energy Content'] < 0:
            if - op_plan.at[t, 'Set Energy Content'] > op_plan.at[t-1, 'max_content']:
                raise ValueError(
                    "For variable load '{}','{}', at timestep {} the given negative 'Set Energy Content' value is not "
                    "physically feasible".format(site_name, file_name, t))
            else:
                op_plan.at[t, 'max_content'] = op_plan.at[t-1, 'max_content'] + op_plan.at[t, 'Set Energy Content']\
                                                 + ((m.valo_dict['max-p'][valo] * dt * m.valo_dict['eff'][valo]) /
                                                m.valo_dict['capacity'][valo])
        if op_plan.at[t, 'max_content'] > 1:
            op_plan.at[t, 'max_content'] = 1
    for t in range(len(op_plan)):
        if op_plan.at[t, 'Energy Content Goal'] > op_plan.at[t, 'max_content']:
            raise ValueError("Energy Content Goal at timestep {} for variable load '{}','{}'  is not physically "
                                 "feasible.".format(t, site_name, file_name))


def add_valo_fix_part_to_demand(m, dt, op_plan, valo):
    # Add the fixed part of the variable load to the demand. It does not have to be distinguished between vehicle and
    # non-vehicle since there was already an error raised for all not allowed states.
    # The calculation of 'Set Energy Content' for the transitions (1-2) and (1-3) is conducted here as well.
    for sit_com, sit_com_demand_dict in m.demand_dict.items():
        if valo[1] == sit_com[0] and valo[3] == sit_com[1]:
            # To give the possibility to reset the energy content during a 'must-operate' period, an interrupted
            # column that is true when there's a 'Set Energy Content' value and State is 1 is added. (1-1 transition)
            op_plan['Interrupted'] = (op_plan['State'] == 1) & (~op_plan['Set Energy Content'].isna())
            # Finding sequences of ones
            op_plan['Group'] = (
                    (op_plan['State'] != op_plan['State'].shift()) | op_plan['Interrupted']).cumsum()
            one_sequences = op_plan[op_plan['State'] == 1].groupby('Group').size()
            start_indices = op_plan[(op_plan['State'] == 1) & (
                    (op_plan['State'] != op_plan['State'].shift()) | op_plan['Interrupted'])].index.tolist()
            one_sequences_tuples = [(transition_ts, length_sequence) for transition_ts, length_sequence in
                                    zip(start_indices, one_sequences.values)]
            op_plan.drop(columns=['Group', 'Interrupted'], inplace=True)
            # Adjust the demand
            for year, ts in sit_com_demand_dict.keys():
                for transition_ts, length_sequence in one_sequences_tuples:
                    if transition_ts == ts:
                        energy_content = op_plan['Set Energy Content'][transition_ts]
                        timesteps_until_full = ((m.valo_dict['capacity'][valo] * (1 - energy_content)) /
                                                (m.valo_dict['max-p'][valo] * m.valo_dict['eff'][valo])) / dt
                        # Check which time factor is limiting
                        if length_sequence <= math.ceil(timesteps_until_full):
                            max_operation_timesteps = length_sequence
                            # It is optional to reset 'Set Energy Content' at the transition from state 1 to 2/3. If no
                            # set energy value is given, it is calculated for the optimization.
                            if op_plan['State'][transition_ts + length_sequence] in [2, 3] and \
                                    pd.isna(op_plan['Set Energy Content'][ts + length_sequence]):
                                op_plan['Set Energy Content'][ts + math.floor(max_operation_timesteps)] = \
                                    op_plan['Set Energy Content'][ts] + (
                                                max_operation_timesteps * dt * m.valo_dict['max-p'][
                                            valo] * m.valo_dict['eff'][valo]) / m.valo_dict['capacity'][valo]
                        else:
                            max_operation_timesteps = timesteps_until_full
                            if op_plan['State'][transition_ts + length_sequence] in [2, 3] and \
                                    pd.isna(op_plan['Set Energy Content'][ts + length_sequence]):
                                op_plan['Set Energy Content'][ts + math.floor(length_sequence)] = \
                                    op_plan['Set Energy Content'][ts] + (
                                                max_operation_timesteps * dt * m.valo_dict['max-p'][
                                            valo] * m.valo_dict['eff'][valo]) / m.valo_dict['capacity'][valo]
                            # Print Warning because the subordinate input logic should not have allowed that
                            print('Warning: The variable load', valo,
                                  'will be full before the end of the must operate '
                                  'period starting at timestep', transition_ts)
                        for i in range(0, math.floor(max_operation_timesteps)):
                            sit_com_demand_dict[year, ts + i] += m.valo_dict['max-p'][valo] * dt
                        # Takes care of the decimal timestep. Also important for storage errors which e.g. result
                        # into 4.999999999
                        sit_com_demand_dict[year,
                                            ts + math.floor(max_operation_timesteps)] += (max_operation_timesteps -
                                                                                          int(max_operation_timesteps)
                                                                                          ) * m.valo_dict['max-p'][
                                                                                                   valo] * dt

    return m


# preparing the pyomo model
def pyomo_model_prep(data, timesteps, dt):
    '''Performs calculations on the data frames in dictionary "data" for
    further usage by the model.

    Args:
        - data: input data dictionary
        - timesteps: range of modeled timesteps

    Returns:
        a rudimentary pyomo.CancreteModel instance
    '''

    m = pyomo.ConcreteModel()

    # Preparations
    # ============
    # Data import. Syntax to access a value within equation definitions looks
    # like this:
    #
    #     storage.loc[site, storage, commodity][attribute]
    #

    m.mode = identify_mode(data)
    m.timesteps = timesteps
    m.global_prop = data['global_prop']
    commodity = data['commodity']
    process = data['process']

    # create no expansion dataframes
    pro_const_cap = process[process['inst-cap'] == process['cap-up']]

    # create list with all support timeframe values
    m.stf_list = m.global_prop.index.levels[0].tolist()
    # creating list wih cost types
    m.cost_type_list = ['Invest', 'Fixed', 'Variable', 'Fuel', 'Environmental']

    # Converting Data frames to dict
    # Data frames that need to be modified will be converted after modification
    m.site_dict = data['site'].to_dict()
    m.demand_dict = data['demand'].to_dict()
    m.supim_dict = data['supim'].to_dict()

    # additional features
    if m.mode['tra']:
        transmission = data['transmission'].dropna(axis=0, how='all')
        # create no expansion dataframes
        tra_const_cap = transmission[
            transmission['inst-cap'] == transmission['cap-up']]

    if m.mode['sto']:
        storage = data['storage'].dropna(axis=0, how='all')
        # create no expansion dataframes
        sto_const_cap_c = storage[storage['inst-cap-c'] == storage['cap-up-c']]
        sto_const_cap_p = storage[storage['inst-cap-p'] == storage['cap-up-p']]

    if m.mode['valo']:
        variableload = data["valo"].dropna(axis=0, how='all')

    if m.mode['dsm']:
        m.dsm_dict = data["dsm"].dropna(axis=0, how='all').to_dict()
    if m.mode['bsp']:
        m.buy_sell_price_dict = \
            data["buy_sell_price"].dropna(axis=0, how='all').to_dict()
        # adding Revenue and Purchase to cost types
        m.cost_type_list.extend(['Revenue', 'Purchase'])
    if m.mode['tve']:
        m.eff_factor_dict = \
            data["eff_factor"].dropna(axis=0, how='all').to_dict()
    if m.mode['tdy']:
        m.typeday = data['type day'].dropna(axis=0, how='all').to_dict()
    else:
        # if mode 'typeday' is not active, create a dict with ones
        temp = pd.DataFrame(index=data['demand'].dropna(axis=0, how='all').index)
        temp['weight_typeday']=1
        m.typeday = temp.to_dict()

    # Create columns of support timeframe values
    commodity['support_timeframe'] = (commodity.index.
                                      get_level_values('support_timeframe'))
    process['support_timeframe'] = (process.index.
                                    get_level_values('support_timeframe'))
    if m.mode['tra']:
        transmission['support_timeframe'] = (transmission.index.
                                             get_level_values
                                             ('support_timeframe'))
    if m.mode['sto']:
        storage['support_timeframe'] = (storage.index.
                                        get_level_values('support_timeframe'))
    if m.mode['valo']:
        variableload['support_timeframe'] = (variableload.index.
                                        get_level_values('support_timeframe'))
    # installed units for intertemporal planning
    if m.mode['int']:
        m.inst_pro = process['inst-cap']
        m.inst_pro = m.inst_pro[m.inst_pro > 0]
        if m.mode['tra']:
            m.inst_tra = transmission['inst-cap']
            m.inst_tra = m.inst_tra[m.inst_tra > 0]
        if m.mode['sto']:
            m.inst_sto = storage['inst-cap-p']
            m.inst_sto = m.inst_sto[m.inst_sto > 0]
        # valo ??
    # process input/output ratios
    m.r_in_dict = (data['process_commodity'].xs('In', level='Direction')
                   ['ratio'].to_dict())
    m.r_out_dict = (data['process_commodity'].xs('Out', level='Direction')
                    ['ratio'].to_dict())

    # process areas
    proc_area = data["process"]['area-per-cap']
    proc_area = proc_area[proc_area >= 0]
    m.proc_area_dict = proc_area.to_dict()

    # input ratios for partial efficiencies
    # only keep those entries whose values are
    # a) positive and
    # b) numeric (implicitely, as NaN or NV compare false against 0)
    r_in_min_fraction = data['process_commodity'].xs('In', level='Direction')
    r_in_min_fraction = r_in_min_fraction['ratio-min']
    r_in_min_fraction = r_in_min_fraction[r_in_min_fraction > 0]
    m.r_in_min_fraction_dict = r_in_min_fraction.to_dict()

    # output ratios for partial efficiencies
    # only keep those entries whose values are
    # a) positive and
    # b) numeric (implicitely, as NaN or NV compare false against 0)
    r_out_min_fraction = data['process_commodity'].xs('Out', level='Direction')
    r_out_min_fraction = r_out_min_fraction['ratio-min']
    r_out_min_fraction = r_out_min_fraction[r_out_min_fraction > 0]
    m.r_out_min_fraction_dict = r_out_min_fraction.to_dict()

    # minimum consecutive operation
    # only keep those entries whose values are
    # a) positive and
    # b) numeric (implicitely, as NaN or NV compare false against 0)
    min_consecutive_op_time = data['process']['min-con-op-time']
    min_consecutive_op_time = min_consecutive_op_time[min_consecutive_op_time > 0]
    m.min_consecutive_op_time_dict = min_consecutive_op_time.to_dict()
    
    # storages with fixed initial state
    if m.mode['sto']:
        stor_init_bound = storage['init']
        m.stor_init_bound_dict = \
            stor_init_bound[stor_init_bound >= 0].to_dict()

        try:
            # storages with fixed energy-to-power ratio
            sto_ep_ratio = storage['ep-ratio']
            m.sto_ep_ratio_dict = sto_ep_ratio[sto_ep_ratio >= 0].to_dict()
        except KeyError:
            m.sto_ep_ratio_dict = {}

    # derive invcost factor from WACC and depreciation duration
    if m.mode['int']:
        # modify pro_const_cap for intertemporal mode
        for index in tuple(pro_const_cap.index):
            stf_process = process.xs((index[1], index[2]), level=(1, 2))
            if (not stf_process['cap-up'].max(axis=0) ==
                    pro_const_cap.loc[index]['inst-cap']):
                pro_const_cap = pro_const_cap.drop(index)

        # derive invest factor from WACC, depreciation and discount untility
        process['discount'] = (m.global_prop.xs('Discount rate', level=1)
                                .loc[m.global_prop.index.min()[0]]['value'])
        process['stf_min'] = m.global_prop.index.min()[0]
        process['stf_end'] = (m.global_prop.index.max()[0] +
                              m.global_prop.loc[
                              (max(commodity.index.get_level_values
                                   ('support_timeframe').unique()),
                               'Weight')]['value'] - 1)
        process['invcost-factor'] = (process.apply(
                                     lambda x: invcost_factor(
                                         x['depreciation'],
                                         x['wacc'],
                                         x['discount'],
                                         x['support_timeframe'],
                                         x['stf_min']),
                                     axis=1))

        # derive overpay-factor from WACC, depreciation and discount untility
        process['overpay-factor'] = (process.apply(
                                     lambda x: overpay_factor(
                                         x['depreciation'],
                                         x['wacc'],
                                         x['discount'],
                                         x['support_timeframe'],
                                         x['stf_min'],
                                         x['stf_end']),
                                     axis=1))
        process.loc[(process['overpay-factor'] < 0) |
                    (process['overpay-factor']
                     .isnull()), 'overpay-factor'] = 0

        # Derive multiplier for all energy based costs
        commodity['stf_dist'] = (commodity['support_timeframe'].
                                 apply(stf_dist, m=m))
        commodity['discount-factor'] = (commodity['support_timeframe'].
                                        apply(discount_factor, m=m))
        commodity['eff-distance'] = (commodity['stf_dist'].
                                     apply(effective_distance, m=m))
        commodity['cost_factor'] = (commodity['discount-factor'] *
                                    commodity['eff-distance'])
        process['stf_dist'] = (process['support_timeframe'].
                               apply(stf_dist, m=m))
        process['discount-factor'] = (process['support_timeframe'].
                                      apply(discount_factor, m=m))
        process['eff-distance'] = (process['stf_dist'].
                                   apply(effective_distance, m=m))
        process['cost_factor'] = (process['discount-factor'] *
                                  process['eff-distance'])

        # Additional features
        # transmission mode
        if m.mode['tra']:
            # modify tra_const_cap for intertemporal mode
            for index in tuple(tra_const_cap.index):
                stf_transmission = transmission.xs((index[1], index[2], index[3], index[4]),
                                                   level=(1, 2, 3, 4))
                if (not stf_transmission['cap-up'].max(axis=0) ==
                        tra_const_cap.loc[index]['inst-cap']):
                    tra_const_cap = tra_const_cap.drop(index)
            # derive invest factor from WACC, depreciation and
            # discount untility
            transmission['discount'] = (
                m.global_prop.xs('Discount rate', level=1)
                .loc[m.global_prop.index.min()[0]]['value'])
            transmission['stf_min'] = m.global_prop.index.min()[0]
            transmission['stf_end'] = (m.global_prop.index.max()[0] +
                                       m.global_prop.loc[
                                       (max(commodity.index.get_level_values
                                            ('support_timeframe').unique()),
                                        'Weight')]['value'] - 1)
            transmission['invcost-factor'] = (
                transmission.apply(lambda x: invcost_factor(
                    x['depreciation'],
                    x['wacc'],
                    x['discount'],
                    x['support_timeframe'],
                    x['stf_min']),
                    axis=1))
            # derive overpay-factor from WACC, depreciation and
            # discount untility
            transmission['overpay-factor'] = (
                transmission.apply(lambda x: overpay_factor(
                    x['depreciation'],
                    x['wacc'],
                    x['discount'],
                    x['support_timeframe'],
                    x['stf_min'],
                    x['stf_end']),
                    axis=1))
            # Derive multiplier for all energy based costs
            transmission.loc[(transmission['overpay-factor'] < 0) |
                             (transmission['overpay-factor'].isnull()),
                             'overpay-factor'] = 0
            transmission['stf_dist'] = (transmission['support_timeframe'].
                                        apply(stf_dist, m=m))
            transmission['discount-factor'] = (
                transmission['support_timeframe'].apply(discount_factor, m=m))
            transmission['eff-distance'] = (transmission['stf_dist'].
                                            apply(effective_distance, m=m))
            transmission['cost_factor'] = (transmission['discount-factor'] *
                                           transmission['eff-distance'])
        # storage mode
        if m.mode['sto']:
            # modify sto_const_cap_c and sto_const_cap_p for intertemporal mode
            for index in tuple(sto_const_cap_c.index):
                stf_storage = storage.xs((index[1], index[2], index[3]), level=(1, 2, 3))
                if (not stf_storage['cap-up-c'].max(axis=0) ==
                        sto_const_cap_c.loc[index]['inst-cap-c']):
                    sto_const_cap_c = sto_const_cap_c.drop(index)

            for index in tuple(sto_const_cap_p.index):
                stf_storage = storage.xs((index[1], index[2], index[3]), level=(1, 2, 3))
                if (not stf_storage['cap-up-p'].max(axis=0) ==
                        sto_const_cap_p.loc[index]['inst-cap-p']):
                    sto_const_cap_p = sto_const_cap_p.drop(index)

            # derive invest factor from WACC, depreciation and
            # discount untility
            storage['discount'] = m.global_prop.xs('Discount rate', level=1) \
                                   .loc[m.global_prop.index.min()[0]]['value']
            storage['stf_min'] = m.global_prop.index.min()[0]
            storage['stf_end'] = (m.global_prop.index.max()[0] +
                                  m.global_prop.loc[
                                  (max(commodity.index.get_level_values
                                       ('support_timeframe').unique()),
                                   'Weight')]['value'] - 1)
            storage['invcost-factor'] = (
                storage.apply(
                    lambda x: invcost_factor(
                        x['depreciation'],
                        x['wacc'],
                        x['discount'],
                        x['support_timeframe'],
                        x['stf_min']),
                    axis=1))
            storage['overpay-factor'] = (
                storage.apply(lambda x: overpay_factor(
                    x['depreciation'],
                    x['wacc'],
                    x['discount'],
                    x['support_timeframe'],
                    x['stf_min'],
                    x['stf_end']),
                    axis=1))

            storage.loc[(storage['overpay-factor'] < 0) |
                        (storage['overpay-factor'].isnull()),
                        'overpay-factor'] = 0

            storage['stf_dist'] = (storage['support_timeframe']
                                   .apply(stf_dist, m=m))
            storage['discount-factor'] = (storage['support_timeframe']
                                          .apply(discount_factor, m=m))
            storage['eff-distance'] = (storage['stf_dist']
                                       .apply(effective_distance, m=m))
            storage['cost_factor'] = (storage['discount-factor'] *
                                      storage['eff-distance'])
    else:
        # for one year problems
        process['invcost-factor'] = (
            process.apply(
                lambda x: invcost_factor(
                    x['depreciation'],
                    x['wacc']),
                axis=1))

        # cost factor will be set to 1 for non intertemporal problems
        commodity['cost_factor'] = 1
        process['cost_factor'] = 1

        # additional features
        if m.mode['tra']:
            transmission['invcost-factor'] = (
                transmission.apply(lambda x:
                                   invcost_factor(x['depreciation'],
                                                  x['wacc']),
                                   axis=1))
            transmission['cost_factor'] = 1
        if m.mode['sto']:
            storage['invcost-factor'] = (
                storage.apply(lambda x:
                              invcost_factor(x['depreciation'],
                                             x['wacc']),
                              axis=1))
            storage['cost_factor'] = 1

    # Converting Data frames to dictionaries
    m.global_prop_dict = m.global_prop.to_dict()
    m.commodity_dict = commodity.to_dict()
    m.process_dict = process.to_dict()

    # dictionaries for additional features
    if m.mode['tra']:
        m.transmission_dict = transmission.to_dict()
        # DCPF transmission lines are bidirectional and do not have symmetry
        # fix-cost and inv-cost should be multiplied by 2
        if m.mode['dpf']:
            transmission_dc = transmission[transmission['reactance'] > 0]
            m.transmission_dc_dict = transmission_dc.to_dict()
            for t in m.transmission_dc_dict['reactance']:
                m.transmission_dict['inv-cost'][t] = 2 * m.transmission_dict['inv-cost'][t]
                m.transmission_dict['fix-cost'][t] = 2 * m.transmission_dict['fix-cost'][t]

    if m.mode['sto']:
        m.storage_dict = storage.to_dict()

    if m.mode['valo']:
        m.valo_dict = variableload.to_dict()
        # Read in the Variable Load operation plans which are stored in different folders
        m = read_in_valo_availability_data(m, timesteps, dt)






    # update m.mode['exp'] and write dictionaries with constant capacities
    m.mode['exp']['pro'] = identify_expansion(pro_const_cap['inst-cap'],
                                              process['inst-cap'].dropna())
    m.pro_const_cap_dict = pro_const_cap['inst-cap'].to_dict()

    if m.mode['tra']:
        m.mode['exp']['tra'] = identify_expansion(
            tra_const_cap['inst-cap'],
            transmission['inst-cap'].dropna())
        m.tra_const_cap_dict = tra_const_cap['inst-cap'].to_dict()

    if m.mode['sto']:
        m.mode['exp']['sto-c'] = identify_expansion(
            sto_const_cap_c['inst-cap-c'], storage['inst-cap-c'].dropna())
        m.sto_const_cap_c_dict = sto_const_cap_c['inst-cap-c'].to_dict()
        m.mode['exp']['sto-p'] = identify_expansion(
            sto_const_cap_c['inst-cap-p'], storage['inst-cap-p'].dropna())
        m.sto_const_cap_p_dict = sto_const_cap_p['inst-cap-p'].to_dict()

    return m


def split_columns(columns, sep='.'):
    """Split columns by separator into MultiIndex.

    Given a list of column labels containing a separator string (default: '.'),
    derive a MulitIndex that is split at the separator string.

    Args:
        - columns: list of column labels, containing the separator string
        - sep: the separator string (default: '.')

    Returns:
        a MultiIndex corresponding to input, with levels split at separator

    Example:
        >>> split_columns(['DE.Elec', 'MA.Elec', 'NO.Wind'])
        MultiIndex(levels=[['DE', 'MA', 'NO'], ['Elec', 'Wind']],
                   labels=[[0, 1, 2], [0, 0, 1]])

    """
    if len(columns) == 0:
        return columns
    column_tuples = [tuple(col.split('.')) for col in columns]
    return pd.MultiIndex.from_tuples(column_tuples)


def get_input(prob, name):
    """Return input DataFrame of given name from urbs instance.

    These are identical to the key names returned by function `read_excel`.
    That means they are lower-case names and use underscores for word
    separation, e.g. 'process_commodity'.

    Args:
        - prob: a urbs model instance
        - name: an input DataFrame name ('commodity', 'process', ...)

    Returns:
        the corresponding input DataFrame

    """
    if hasattr(prob, name):
        # classic case: input data DataFrames are accessible via named
        # attributes, e.g. `prob.process`.
        return getattr(prob, name)
    elif hasattr(prob, '_data') and name in prob._data:
        # load case: input data is accessible via the input data cache dict
        return prob._data[name]
    else:
        # unknown
        raise ValueError("Unknown input DataFrame name!")
