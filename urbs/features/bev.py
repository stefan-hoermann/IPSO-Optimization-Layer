import pyomo.core as pyomo
import pandas as pd
import os
import numpy as np

def add_bev(m):
    indexlist = set()
    for key in m.bev_dict["capacity"]:
        indexlist.add(tuple(key)[2])
    m.bev = pyomo.Set(
        initialize=indexlist,
        doc='Set of bevs')

    m = read_in_bev_availability_data(m)

    # BEV tuples
    m.bev_tuples = pyomo.Set(
        within=m.stf * m.sit * m.bev * m.com,
        initialize=tuple(m.bev_dict["capacity"].keys()),
        doc='Combinations of possible storage by site,'
            'e.g. (2020,Mid,Bat,Elec)')


    # Variables
    m.e_bev_in = pyomo.Var(
        m.tm, m.bev_tuples,
        within=pyomo.NonNegativeReals,
        doc='Power flow into bev (MW) per timestep')

    m.e_bev_con = pyomo.Var(
        m.t, m.bev_tuples,
        within=pyomo.NonNegativeReals,
        doc='Energy content of bev (MWh) in timestep')

    m.bev_mode_run = pyomo.Var(
        m.t, m.bev_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if bev is charging')

    # Restrictions
    m.def_bev_state = pyomo.Constraint(
        m.tm, m.bev_tuples,
        rule=def_bev_state_rule,
        doc='SOC[t] = SOC[t-1] + e_in')
    m.def_bev_init_state = pyomo.Constraint(
        m.tm, m.bev_tuples,
        rule=def_bev_init_state_rule,
        doc='SOC[0] = init SOC')
    m.res_bev_state_by_capacity = pyomo.Constraint(
        m.t, m.bev_tuples,
        rule=res_bev_state_by_capacity_rule,
        doc='storage content <= storage capacity')
    m.res_bev_input_by_power = pyomo.Constraint(
        m.tm, m.bev_tuples,
        rule=res_bev_input_by_power_rule,
        doc='bev input <= bev power')
    m.res_charge_goal_1 = pyomo.Constraint(
        m.tm, m.bev_tuples,
        rule=res_charge_goal_1_rule,
        doc='reach SOC1 xy at time t1')
    m.res_charge_goal_2 = pyomo.Constraint(
        m.tm, m.bev_tuples,
        rule=res_charge_goal_2_rule,
        doc='reach SOC2 xy at time t2')



    return m


# SOC[t] = SOC[t-1] + e_in
def def_bev_state_rule(m, t, stf, sit, bev, com):
    return m.e_bev_con[t, stf, sit, bev, com] == m.e_bev_con[t-1, stf, sit, bev, com] + m.e_bev_in[t, stf, sit, bev, com]


def def_bev_init_state_rule(m, t, stf, sit, bev, com):
    return m.e_bev_con[0, stf, sit, bev, com] == m.bev_dict['start-soc'][(stf, sit, bev, com)] * \
           m.bev_dict['capacity'][(stf, sit, bev, com)]


def res_bev_state_by_capacity_rule(m, t, stf, sit, bev, com):
    return m.e_bev_con[t, stf, sit, bev, com] <= m.bev_dict['capacity'][(stf, sit, bev, com)]


# bev input <= bev power
def res_bev_input_by_power_rule(m, t, stf, sit, bev, com):
    return m.e_bev_in[t, stf, sit, bev, com] <= m.bev_dict['max-p'][(stf, sit, bev, com)] *\
           m.bev_availability_data[bev][t]


# Reach first charging goal at given time
def res_charge_goal_1_rule(m, t, stf, sit, bev, com):
    return m.e_bev_con[m.bev_dict['t-first-cg'][(stf, sit, bev, com)], stf, sit, bev, com] >= \
           m.bev_dict['first-cg'][(stf, sit, bev, com)] * m.bev_dict['capacity'][(stf, sit, bev, com)]


# Reach second charging goal at given time
def res_charge_goal_2_rule(m, t, stf, sit, bev, com):
    return m.e_bev_con[m.bev_dict['t-second-cg'][(stf, sit, bev, com)], stf, sit, bev, com] >= \
           m.bev_dict['second-cg'][(stf, sit, bev, com)] * m.bev_dict['capacity'][(stf, sit, bev, com)]


def bev_balance(m, tm, stf, sit, com):
    """called in commodity balance
    For a given commodity co and timestep tm, calculate the balance of
    bev input """

    return sum(m.e_bev_in[(tm, stframe, site, bev, com)]
               # usage as input for bev increases consumption
               for stframe, site, bev, commodity in m.bev_tuples
               if site == sit and stframe == stf and commodity == com)


def read_in_bev_availability_data(m):
    input_dir = r"C:\Users\steft\OneDrive\Desktop\Uni\Master\Masterarbeit\Python\urbs-MILP\Input BEV"
    input_files = os.listdir(input_dir)
    if len(input_files) > 1:
        raise ValueError("There should only be one file in the Input MILP folder. ")
    file_name = input_files[0]
    file_path = os.path.join(input_dir, file_name)
    bev_data = pd.read_csv(file_path, sep=";", index_col=0)
    bev_data = bev_data.astype(bool)
    m.bev_availability_data = bev_data.to_dict(orient='series')
    return m

