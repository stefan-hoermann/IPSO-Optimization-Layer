import pyomo.core as pyomo
import pandas as pd
import os
import numpy as np


# Variable Load. Valo allowes the modelling of different kinds of variable loads such as E-Cars, E-Forklifts and any
# kind of machine. As of now, there are several limitations:
# - Efficiency constant
# - Only one commodity
# - No min operation time or other restrictions.
# Valo has its own input in the "Input Variable Load" folder. This folder must contain a folder for each site which in
# turn must contain one file named like the corresponding valo in the general input file. See my thesis and the example
# file for the structure of the valo.csv files.
# Valo supports different sites and remains the same for all support timeframes. Additionally, only one commodity is
# regarded (as specified in the Input file). To model a valo with multiple commodities, the following logic has to be
# extended in analogy to the implementation of a process.
def add_valo(m):
    indexlist = set()
    for key in m.valo_dict["capacity"]:
        indexlist.add(tuple(key)[2])
    m.valo = pyomo.Set(
        initialize=indexlist,
        doc='Set of valos')

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

    m.e_valo_reset = pyomo.Var(
        m.t, m.valo_tuples,
        within=pyomo.NonNegativeReals,
        doc='Energy content of valo (MWh) at the timestep of the reset')


    # Restrictions
    m.def_valo_state = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=def_valo_state_rule,
        doc='SOC[t] = SOC[t-1] + e_in')
    m.def_valo_reset = pyomo.Constraint(
        m.tm, m.valo_tuples,
        rule=def_valo_reset_rule,
        doc='storage content reset')
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

    for (site_name, valo_name) in m.valo_operation_plan_dict:
        for stf, sit, v, com in m.valo_tuples:
            if v == valo_name and sit == site_name:
                # Adding constraints for Energy Content Goals at specified time points
                for goal_time in m.valo_operation_plan_dict[(sit, valo_name)]['production_goals']:
                    m.add_component(
                        f"res_production_goal_{goal_time}_{stf}_{sit}_{valo_name}_{com}",
                        pyomo.Constraint(
                            rule=lambda m, t=goal_time, stf=stf, sit=sit, valo=valo_name, com=com:
                            res_production_goal_rule(m, t, stf, sit, valo_name, com)
                        )
                    )

    return m


# E_con(t) = E_con(t-1) * (1-reset[t]) +
#            E_reset(t) * reset[t] +
#            e_in * eff
def def_valo_state_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[t, stf, sit, valo, com] == \
           m.e_valo_con[t-1, stf, sit, valo, com] * (1 - m.valo_operation_plan_dict[(sit, valo)]['reset'].loc[t]) + \
           m.e_valo_reset[t, stf, sit, valo, com] * m.valo_operation_plan_dict[(sit, valo)]['reset'].loc[t] + \
           m.e_valo_in[t, stf, sit, valo, com] * m.valo_dict['eff'][(stf, sit, valo, com)]


# E_reset(t) is the value to which the energy content gets reset to. There are two different approaches on how this
# input can be given. In the first approach the energy content is absolute-set, this means a specific absolute energy
# content is set regardless of the past. This is achieved by giving a fraction of the max capacity as energy content.
# In the second approach, the relative-set, a negative delta which is subtracted from the last energy content is given.
# In case of a BEV, this simulates that the vehicle was in use and thus discharged before returning. The SOC is in this
# case still dependent on what was charged before the vehicle left for the pause period.
def def_valo_reset_rule(m, t, stf, sit, valo, com):
    if m.valo_operation_plan_dict[(sit, valo)]['set_energy_content'][t] > 0:
        return m.e_valo_reset[t, stf, sit, valo, com] == m.valo_operation_plan_dict[(sit, valo)]['set_energy_content'][t] * \
               m.valo_dict['capacity'][(stf, sit, valo, com)]
    elif m.valo_operation_plan_dict[(sit, valo)]['set_energy_content'][t] < 0:
        return m.e_valo_reset[t, stf, sit, valo, com] == \
               m.e_valo_con[t-1, stf, sit, valo, com] + \
               m.valo_operation_plan_dict[(sit, valo)]['set_energy_content'][t] * m.valo_dict['capacity'][(stf, sit, valo, com)]
    else:
        if t == 1:
            return m.e_valo_reset[t, stf, sit, valo, com] == 0
        else:
            return m.e_valo_reset[t, stf, sit, valo, com] == m.e_valo_con[t-1, stf, sit, valo, com]
        # return pyomo.Constraint.Skip


# E_con(t) <= SOCmax
def res_valo_state_by_capacity_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[t, stf, sit, valo, com] <= m.valo_dict['capacity'][(stf, sit, valo, com)]


# e_in(t) <= max_power * availability * run(t) * dt
def res_valo_input_by_power_rule_max(m, t, stf, sit, valo, com):
    return m.e_valo_in[t, stf, sit, valo, com] <= m.valo_dict['max-p'][(stf, sit, valo, com)] * \
           m.valo_operation_plan_dict[(sit, valo)]['state'].loc[t] * m.valo_mode_run[t, stf, sit, valo, com] * m.dt


# e_in(t) >= min_power * availability * run(t)
def res_valo_input_by_power_rule_min(m, t, stf, sit, valo, com):
    return m.e_valo_in[t, stf, sit, valo, com] >= m.valo_dict['min-p'][(stf, sit, valo, com)] * \
           m.valo_operation_plan_dict[(sit, valo)]['state'].loc[t] * m.valo_mode_run[t, stf, sit, valo, com] * m.dt


# Reach Energy Content Goal at given time as defined in the valo_input file
def res_production_goal_rule(m, t, stf, sit, valo, com):
    return m.e_valo_con[t, stf, sit, valo, com] >= m.valo_operation_plan_dict[(sit, valo)]['production_goals'][t] \
           * m.valo_dict['capacity'][(stf, sit, valo, com)]


def valo_balance(m, tm, stf, sit, com):
    """called in commodity balance
    For a given commodity co and timestep tm, calculate the balance of
    valo input """

    return sum(m.e_valo_in[(tm, stframe, site, valo, com)]
               # usage as input for valo increases consumption
               for stframe, site, valo, commodity in m.valo_tuples
               if site == sit and stframe == stf and commodity == com)




