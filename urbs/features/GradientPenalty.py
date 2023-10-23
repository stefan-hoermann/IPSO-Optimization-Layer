import pyomo.core as pyomo
import pandas as pd


def add_gradient_penalty(m):
    # A penalty is applied on the gradient of processes and storage systems toa void th erapid change of output power.
    # penalty = abs(tau(t) - tau(t-1)) * penalty_factor
    # Abs() is non-linear, linearization:
    # slack1, slack2 >= 0
    # tau(t) - tau(t-1) = slack1 - slack2
    # penalty = (slack1 + slack2) * penalty_factor
    m.pro_gradient_penalty_slack_1 = pyomo.Var(
        m.t, m.pro_tuples,
        within=pyomo.NonNegativeReals,
        doc='Slack 1 for process gradient penalty')

    m.pro_gradient_penalty_slack_2 = pyomo.Var(
        m.t, m.pro_tuples,
        within=pyomo.NonNegativeReals,
        doc='Slack 2 for process gradient penalty')

    m.res_pro_gradient_penalty = pyomo.Constraint(
        m.tm, m.pro_tuples,
        rule=res_pro_gradient_penalty,
        doc='Process gradient penalty.')

    m.sto_in_gradient_penalty_slack_1 = pyomo.Var(
        m.t, m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Slack 1 for storage input gradient penalty')

    m.sto_in_gradient_penalty_slack_2 = pyomo.Var(
        m.t, m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Slack 2 for storage input gradient penalty')

    m.sto_out_gradient_penalty_slack_1 = pyomo.Var(
        m.t, m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Slack 1 for storage input gradient penalty')

    m.sto_out_gradient_penalty_slack_2 = pyomo.Var(
        m.t, m.sto_tuples,
        within=pyomo.NonNegativeReals,
        doc='Slack 2 for storage input gradient penalty')

    m.res_sto_in_gradient_penalty = pyomo.Constraint(
        m.tm, m.sto_tuples,
        rule=res_sto_in_gradient_penalty,
        doc='Storage input gradient penalty.')
    m.res_sto_out_gradient_penalty = pyomo.Constraint(
        m.tm, m.sto_tuples,
        rule=res_sto_out_gradient_penalty,
        doc='Storage output gradient penalty.')
    # m.res_sto_in_out_penalty = pyomo.Constraint(
    #     m.tm, m.sto_tuples,
    #     rule=res_sto_in_out_penalty,
    #     doc='Storage output gradient penalty.')

    return m


def res_sto_in_gradient_penalty(m, tm, stf, sit, sto, com):
    if tm == 1:
        return pyomo.Constraint.Skip
    else:
        return m.e_sto_in[tm, stf, sit, sto, com] - m.e_sto_in[tm-1, stf, sit, sto, com] == \
           m.sto_in_gradient_penalty_slack_1[tm, stf, sit, sto, com] - m.sto_in_gradient_penalty_slack_2[tm, stf, sit, sto, com]


def res_sto_out_gradient_penalty(m, tm, stf, sit, sto, com):
    if tm == 1:
        return pyomo.Constraint.Skip
    else:
        return m.e_sto_out[tm, stf, sit, sto, com] - m.e_sto_out[tm-1, stf, sit, sto, com] == \
           m.sto_out_gradient_penalty_slack_1[tm, stf, sit, sto, com] - m.sto_out_gradient_penalty_slack_2[tm, stf, sit, sto, com]


def calculate_sto_gradient_penalty(m):
    return sum((m.sto_in_gradient_penalty_slack_1[tm, s] + m.sto_in_gradient_penalty_slack_2[tm, s] +
                m.sto_out_gradient_penalty_slack_1[tm, s] + m.sto_out_gradient_penalty_slack_2[tm, s]) * m.storage_dict['grad-penalty'][(s)]
                for tm in m.tm
                for s in m.sto_tuples)


def res_sto_in_out_penalty(m, tm, stf, sit, sto, com):
    return m.e_sto_in[tm, stf, sit, sto, com] != m.e_sto_out[tm, stf, sit, sto, com]


def res_pro_gradient_penalty(m, tm, stf, sit, pro):
    return m.tau_pro[tm, stf, sit, pro] - m.tau_pro[tm-1, stf, sit, pro] == \
           m.pro_gradient_penalty_slack_1[tm, stf, sit, pro] - m.pro_gradient_penalty_slack_2[tm, stf, sit, pro]


# Process
def calculate_pro_gradient_penalty(m):
    return sum((m.pro_gradient_penalty_slack_1[tm, p] + m.pro_gradient_penalty_slack_2[tm, p]) * m.process_dict['grad-penalty'][(p)]
        for tm in m.tm
        for p in m.pro_tuples)