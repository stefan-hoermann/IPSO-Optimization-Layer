import pyomo.core as pyomo
import pandas as pd
import os
import numpy as np


# Variable Load. Valo allowes the modelling of different kinds of variable loads such as E-Cars, E-Forklifts and any
# kind of machine. As of now, there are several limitations require future implementations.
# Limitations:
# - Efficiency constant
# - Only one commodity
# - Only two production goals (pg)
# - No min operation time
def add_valo(m):
    indexlist = set()
    for key in m.valo_dict["capacity"]:
        indexlist.add(tuple(key)[2])
    m.valo = pyomo.Set(
        initialize=indexlist,
        doc='Set of valos')

    m = read_in_valo_availability_data(m)

    # valo tuples
    m.valo_tuples = pyomo.Set(
        within=m.stf * m.sit * m.valo * m.com,
        initialize=tuple(m.valo_dict["capacity"].keys()),
        doc='Combinations of possible storage by site,'
            'e.g. (2020,Mid,Bat,Elec)')


    # Variables
    m.valo_mode_run = pyomo.Var(
        m.t, m.valo_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if valo is actively operating')

    m.e_valo_in = pyomo.Var(
        m.tm, m.valo_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow into valo (MW) per timestep')

    m.e_valo_con = pyomo.Var(
        m.t, m.valo_tuples,
        within=pyomo.NonNegativeReals,
        doc='Energy content of valo (MWh) in timestep')


    # Restrictions
    m.def_valo_state = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=def_valo_state_rule,
        doc='SOC[t] = SOC[t-1] + e_in')
    m.def_valo_init_state = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=def_valo_init_state_rule,
        doc='SOC[0] = init SOC')
    m.res_valo_state_by_capacity = pyomo.Constraint(
        m.t, m.valo_tuples,
        rule=res_valo_state_by_capacity_rule,
        doc='storage content <= storage capacity')
    m.res_valo_input_by_power_max = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=res_valo_input_by_power_rule_max,
        doc='e_in(t) <= max_power * availability * run(t)')
    m.res_valo_input_by_power_min = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=res_valo_input_by_power_rule_min,
        doc='e_in(t) >= min_power * availability * run(t)')
    m.res_charge_goal_1 = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=res_charge_goal_1_rule,
        doc='reach SOC1 xy at time t1')
    m.res_charge_goal_2 = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=res_charge_goal_2_rule,
        doc='reach SOC2 xy at time t2')

    return m


# SOC[t] = SOC[t-1] + e_in * eff
def def_valo_state_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[t, stf, sit, valo, com] == m.e_valo_con[t-1, stf, sit, valo, com] +\
           m.e_valo_in[t, stf, sit, valo, com] * m.valo_dict['eff'][(stf, sit, valo, com)]

# SOC[0] = start SOC
def def_valo_init_state_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[0, stf, sit, valo, com] == m.valo_dict['start-soc'][(stf, sit, valo, com)] * \
           m.valo_dict['capacity'][(stf, sit, valo, com)]


# SOC(t) < SOCmax
def res_valo_state_by_capacity_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[t, stf, sit, valo, com] <= m.valo_dict['capacity'][(stf, sit, valo, com)]


# e_in(t) <= max_power * availability * run(t)
def res_valo_input_by_power_rule_max(m, t, stf, sit, valo, com):
    return m.e_valo_in[t, stf, sit, valo, com] <= m.valo_dict['max-p'][(stf, sit, valo, com)] *\
           m.valo_availability_data[valo][t] * m.valo_mode_run[t, stf, sit, valo, com]


# e_in(t) >= min_power * availability * run(t)
def res_valo_input_by_power_rule_min(m, t, stf, sit, valo, com):
    return m.e_valo_in[t, stf, sit, valo, com] <= m.valo_dict['max-p'][(stf, sit, valo, com)] *\
           m.valo_availability_data[valo][t]

# Reach first production goal at given time
def res_charge_goal_1_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[m.valo_dict['t-first-pg'][(stf, sit, valo, com)], stf, sit, valo, com] >= \
           m.valo_dict['first-pg'][(stf, sit, valo, com)] * m.valo_dict['capacity'][(stf, sit, valo, com)]


# Reach second production goal at given time
def res_charge_goal_2_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[m.valo_dict['t-second-pg'][(stf, sit, valo, com)], stf, sit, valo, com] >= \
           m.valo_dict['second-pg'][(stf, sit, valo, com)] * m.valo_dict['capacity'][(stf, sit, valo, com)]


def valo_balance(m, tm, stf, sit, com):
    """called in commodity balance
    For a given commodity co and timestep tm, calculate the balance of
    valo input """

    return sum(m.e_valo_in[(tm, stframe, site, valo, com)]
               # usage as input for valo increases consumption
               for stframe, site, valo, commodity in m.valo_tuples
               if site == sit and stframe == stf and commodity == com)


# Reads in the availability data
def read_in_valo_availability_data(m):
    input_dir = "Input Variable Load"
    input_files = os.listdir(input_dir)
    if len(input_files) > 1:
        raise ValueError("There should only be one file in the Input MILP folder. ")
    file_name = input_files[0]
    file_path = os.path.join(input_dir, file_name)
    valo_data = pd.read_csv(file_path, sep=";", index_col=0)
    valo_data = valo_data.astype(bool)
    m.valo_availability_data = valo_data.to_dict(orient='series')
    return m

