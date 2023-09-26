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

    m.valo_input_dict = {}
    m.valo_operate_immediate = {}

    for site_dir in site_dirs:
        site_input_dir = os.path.join(input_dir, site_dir)
        input_files = os.listdir(site_input_dir)

        for file_name in input_files:
            file_path = os.path.join(site_input_dir, file_name)
            valo_data = pd.read_csv(file_path, sep=";", index_col=0)
            if len(valo_data) < timesteps.stop:
                raise ValueError(
                    "The input file '{}', '{}' is too short. It should have at least {} entries.".format(site_dir,
                                                                                                         file_name,
                                                                                                         timesteps))
            else:
                valo_data = valo_data.iloc[:timesteps.stop]

            valo_data['Energy Start'] = valo_data['Energy Start'].replace(',', '.', regex=True)
            valo_data['Energy Start'] = pd.to_numeric(valo_data['Energy Start'], errors='coerce')

            valo_data['Energy Required'] = valo_data['Energy Required'].replace(',', '.', regex=True)
            valo_data['Energy Required'] = pd.to_numeric(valo_data['Energy Required'], errors='coerce')

            file_name = os.path.splitext(file_name)[0]
            site_name = os.path.splitext(site_dir)[0]
            keytuple = tuple(m.valo_dict["capacity"].keys())
            valo_tuple = [tpl for tpl in keytuple if tpl[1] == site_name and tpl[2] == file_name]
            if len(valo_tuple) != 0:
                valo = valo_tuple[0]
                validate_valo_input_files(m, dt, site_name, file_name, valo_data, valo)
            # else:
            #     raise ValueError("There is no master data in the input file for the variable load '{}',"
            #                      "'{}' ".format(site_name, file_name))

            production_goals = {}
            for timestep in valo_data.index:
                energy_required = valo_data.loc[timestep, 'Energy Required']
                if pd.notna(energy_required):
                    production_goals[timestep] = energy_required

            # Create new dataframes to separate fixed and variable load
            charge_immediate_df = valo_data[valo_data['State'] == 1].copy()
            charge_immediate_df = charge_immediate_df.reindex(valo_data.index)
            charge_immediate_df['State'].fillna(0, inplace=True)
            operation_plan = valo_data[(valo_data['State'] == 2) | (valo_data['State'] == 3)].copy()
            operation_plan = operation_plan.reindex(valo_data.index)
            # Replace State 2 "Operate with goal" and State 3 "Operate with Sun" with 1 for binary calculation.
            # State 2 and 3 are basically the same only that there is a OSC required given for State 2.
            operation_plan['State'].replace({2: 1, 3: 1}, inplace=True)
            operation_plan['State'].fillna(0, inplace=True)

            site_valo_key = (site_name, file_name)

            m.valo_input_dict[site_valo_key] = {
                'start_energy_contents': operation_plan['Energy Start'],
                'production_goals': production_goals,
                'State': operation_plan['State']
            }

            m.valo_operate_immediate[site_valo_key] = charge_immediate_df

    # Add the fixed part of the variable load to the demand:
    for key, subdict in m.demand_dict.items():
        # demand_dict only contains the site and the commodity
        select_site, select_comm = key
        # Get the tuples from the input file to match the valos to the commodities & sites in the demand_dict
        keytuple = tuple(m.valo_dict["capacity"].keys())
        valo_site_commodity = [tpl for tpl in keytuple if tpl[1] == select_site and tpl[3] == select_comm]
        for valo in valo_site_commodity:
            operate_immediate = m.valo_operate_immediate[valo[1], valo[2]]
            # Finding the indices where a change from 0 (not operatable) to 1 (operate immediately) occurs
            change_indices = operate_immediate[operate_immediate['State'].diff() == 1].index.tolist()
            # Finding the lengths of sequences of ones
            operate_immediate['Group'] = (
                        operate_immediate['State'] != operate_immediate['State'].shift()).cumsum()
            one_sequences = operate_immediate[operate_immediate['State'] == 1].groupby('Group').size()
            # Creating a list of tuples with index and length of each one sequence
            one_sequences_tuples = [(index, length) for index, length in
                                    zip(change_indices, one_sequences.values)]
            operate_immediate.drop(columns=['Group'], inplace=True)
            # Adjust the demand
            for subkey in subdict.keys():
                year, idx = subkey
                for valo_index, max_avilable_timesteps in one_sequences_tuples:
                    if valo_index == idx:
                        energy_content = operate_immediate['Energy Start'][valo_index]
                        timesteps_until_full = ((m.valo_dict['capacity'][valo] * (1 - energy_content)) /
                                                (m.valo_dict['max-p'][valo] * m.valo_dict['eff'][valo])) / dt
                        # Check which time factor is limiting
                        if max_avilable_timesteps <= math.ceil(timesteps_until_full):
                            max_operation_timesteps = max_avilable_timesteps
                        else:
                            max_operation_timesteps = timesteps_until_full
                            # Print Warning because the subordinate input logic should not have allowed that
                            print('Warning: The variable load', valo,
                                  'will be full before the end of the must operate '
                                  'period starting at timestep', valo_index)
                        for i in range(0, math.floor(max_operation_timesteps)):
                            subdict[year, idx + i] += m.valo_dict['max-p'][valo] * dt
                        # Takes care of the decimal timestep. Also important for storage errors which e.g. result
                        # into 4.999999999
                        subdict[year, idx + math.floor(max_operation_timesteps)] += (max_operation_timesteps -
                                                                                     int(max_operation_timesteps)) * \
                                                                                    m.valo_dict['max-p'][
                                                                                        valo] * dt

    return m


def validate_valo_input_files(m, dt, site_name, file_name, valo_data, valo):
    # Ensure State only contains 0,1,2,3:
    unique_states = valo_data['State'].unique()
    allowed_values = {0, 1, 2, 3}
    invalid_values = set(unique_states) - allowed_values
    if invalid_values:
        invalid_indices = valo_data[valo_data['State'].isin(invalid_values)].index.tolist()
        raise ValueError("The 'State' column in '{}', '{}' contains the invalid"
                         " values: {} at indicenoons {}".format(site_name, file_name, invalid_values, invalid_indices))

    # Ensure -1 < energy content start < 1
    valid_values = valo_data['Energy Start'][pd.notna(valo_data['Energy Start'])]
    if not ((valid_values >= -1) & (valid_values <= 1)).all():
        raise ValueError(
            "All values in the 'Energy Start' column of '{}', '{}' should be between -1 and 1.".format(site_name, file_name))

    # Ensure 0 < energy required < 1
    valid_values = valo_data['Energy Required'][pd.notna(valo_data['Energy Required'])]
    if not ((valid_values > 0) & (valid_values <= 1)).all():
        raise ValueError(
            "All values in the 'Energy Required' column of '{}', '{}' should be between 0 and 1.".format(site_name, file_name))

    # Ensure that there is no 'Energy Start' and 'Energy Required' value given for the same timestep
    invalid_indices = valo_data[valo_data['Energy Start'].notna() & valo_data['Energy Required'].notna()].index
    if not invalid_indices.empty:
        raise ValueError(
            "In '{}', there should not be a 'Energy Start' and a 'Energy Required' value given for the same "
            "timestep {}.".format(file_name, invalid_indices[0]))

    # Ensure that there are only allowed transitions occuring
    transitions = []
    for idx in range(len(valo_data) - 1):
        current_state = valo_data['State'].iloc[idx]
        next_state = valo_data['State'].iloc[idx + 1]
        transitions.append((idx, current_state, next_state))
    for idx, first, second in transitions:
        #### Energy Required ####
        # Ensure that there is no 'Energy Required' value given for the first timestep
        if idx == 0 or idx == 1:
            if pd.notna(valo_data.loc[idx, 'Energy Required']):
                raise ValueError(
                    "There should not be any 'Energy Required' value given for timesteps '0' and '1' in '{}',"
                    " '{}'".format(site_name, file_name))
        # Ensure that there is a "Energy Required" value set where the state is 2 and the next state is not 2.
        if first == 2 and second != 2:
            if pd.isna(valo_data.loc[idx, 'Energy Required']):
                raise ValueError(
                    "In '{}', '{}' there is no 'Energy required' value set at index {} where there's a transition "
                    "from state 2.".format(site_name, file_name, idx))
        # Ensure that there is only a "Energy Required" value if the State is 2
        if first != 2:
            if pd.notna(valo_data.loc[idx, 'Energy Required']):
                raise ValueError(
                    "A 'Energy Required' value can only be set for state 2 'operate with goal' "
                    "(Found in '{}', '{}' at index {}).".format(site_name, file_name, idx))
        #### Energy Start ####
        # Ensure that there is no 'Energy Start' value given for the first timestep
        if idx == 0:
            if pd.notna(valo_data.loc[idx, 'Energy Start']):
                raise ValueError(
                    "There should not be any 'Energy Start' value given for timestep '0' in '{}', '{}'".format(
                        site_name, file_name))
        ## NO_Vehicle ##
        # If the valo is not a vehicle, there are less restrictions:
        if m.valo_dict['is-vehicle'][valo] == 0:
            # Ensure that there is no "Energy Start" Value given if there is a to-zero state transition.
            if second == 0:
                if pd.notna(valo_data.loc[idx+1, 'Energy Start']):
                    raise ValueError(
                        "In '{}', '{}' there should be no 'Energy Start' value set for the transition from state {} to"
                        " state {} at index {}.".format(site_name, file_name, first, second, idx + 1))

            # Ensure that there is a "Energy Start" Value given for required transitions. For non-vehicle variable loads
            # a new "Energy Start" Value can always be given as long as the state is not 0. Exclusion for Vehicles is
            # checked later.
            elif (first, second) in [(0, 1), (0, 2), (0, 3), (2, 1), (3, 1), (3, 2)]:
                if pd.isna(valo_data.loc[idx+1, 'Energy Start']):
                    raise ValueError(
                        "In '{}', '{}' there is no 'Energy Start' value set at index {} where there's a transition "
                        "from state {} to state {}.".format(site_name, file_name, idx + 1, first, second))
            elif (first, second) in [(1, 2), (1, 3)]:
                if pd.isna(valo_data.loc[idx + 1, 'Energy Start']):
                    print("HI")
                    # take calc
            # Ensure that if there is no "Energy Start" given for transition 2-3 that the "Energy Required" of 2 is
            # taken.
            elif (first, second) in [(2, 3)]:
                if pd.isna(valo_data.loc[idx + 1, 'Energy Start']):
                    valo_data.loc[idx + 1, 'Energy Start'] = valo_data.loc[idx, 'Energy Required']
        ## Vehicle ##
        # If the valo is a vehicle, there are aggravated restrictions:
        elif m.valo_dict['is-vehicle'][valo] == 1:
            # If the valo is a vehicle, transitions 2-1, 3-1, and 3-2 are logically impossible.
            if (first, second) in [(2, 1), (3, 1), (3, 2)]:
                raise ValueError("In '{}', '{}', there is an illegal state transition at index {} from state'{}' to "
                                 "state '{}'. Since the valo is defined as a vehicle (set in the input file) these "
                                 "transitions are illegal.".format(site_name, file_name, idx, first, second))
            # Ensure that there is no "Energy Start" Value given for not allowed transitions.
            if (first, second) not in [(0, 1), (0, 2), (0, 3)]:
                if pd.notna(valo_data.loc[idx + 1, 'Energy Start']):
                    raise ValueError(
                        "In '{}', '{}' of type 'is-vehicle' = {} there should be no 'Energy Start' value set for the"
                        " transition from state {} to state {} at index {}.".format(site_name, file_name,
                                                                                    m.valo_dict['is-vehicle'][valo],
                                                                                    first, second, idx + 1))
            else:
                if pd.isna(valo_data.loc[idx+1, 'Energy Start']):
                    raise ValueError(
                        "In '{}', '{}' there is no 'Energy Start' value set at index {} where there's a transition "
                        "from state {} to state {}.".format(site_name, file_name, idx + 1, first, second))
            if (first, second) in [(2, 3)]:
                valo_data.loc[idx + 1, 'Energy Start'] = valo_data.loc[idx, 'Energy Required']
            elif (first, second) in [(1, 2), (1, 3)]:
                print("HI")
                # calc it
        else:
            raise ValueError(
                "In the Input file 'is-vehicle' has to be 0 or 1 for  '{}', '{}'.".format(
                    site_name, file_name))

    # Ensure that the operation plan is physically feasible.
    # Max Energy Content theoretically column denotes the maximum physically possible energy content.
    valo_data['max_content'] = np.nan
    valo_data.at[0, 'max_content'] = 0
    for t in range(1, len(valo_data)):
        if pd.isna(valo_data.at[t, 'Energy Start']):
            active = 1 if valo_data.at[t, 'State'] > 0 else 0
            valo_data.at[t, 'max_content'] = valo_data.at[t-1, 'max_content'] + \
                                             ((m.valo_dict['max-p'][valo] * dt * m.valo_dict['eff'][valo]) /
                                              m.valo_dict['capacity'][valo]) * active
        elif valo_data.at[t, 'Energy Start'] > 0:
            valo_data.at[t, 'max_content'] = valo_data.at[t, 'Energy Start'] + ((m.valo_dict['max-p'][valo] *
                                                                                dt * m.valo_dict['eff'][valo]) /
                                                                                m.valo_dict['capacity'][valo])
        elif valo_data.at[t, 'Energy Start'] < 0:
            if - valo_data.at[t, 'Energy Start'] > valo_data.at[t-1, 'max_content']:
                raise ValueError(
                    "For variable load '{}','{}', at timestep {} the given negative 'Energy Start' value is not "
                    "physically feasible".format(site_name, file_name, t))
            else:
                valo_data.at[t, 'max_content'] = valo_data.at[t-1, 'max_content'] + valo_data.at[t, 'Energy Start']\
                                                 + ((m.valo_dict['max-p'][valo] * dt * m.valo_dict['eff'][valo]) /
                                                m.valo_dict['capacity'][valo])
        if valo_data.at[t, 'max_content'] > 1:
            valo_data.at[t, 'max_content'] = 1
    for t in range(len(valo_data)):
        if valo_data.at[t, 'Energy Required'] > valo_data.at[t, 'max_content']:
            raise ValueError("Energy required at timestep {} for variable load '{}','{}'  is not physically "
                                 "feasible.".format(t, site_name, file_name))


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
