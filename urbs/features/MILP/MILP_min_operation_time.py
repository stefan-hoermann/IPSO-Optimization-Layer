import pyomo.core as pyomo
import pandas as pd

# Ensures a minimum consecutive operation time
def MILP_min_operation_time(m):
    m.def_pro_min_cons_op_time = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=def_pro_min_cons_op_time_rule,
        doc='run[t] >= (1- (run[t-1] * ... * run[t-n]) * run[t-1]')

    return m

def def_pro_min_cons_op_time_rule(m, tm, stf, sit, pro):
    # run(t)>= (1 - run(t-1) * run(t-2)).... * run(t-1)
    # Problem non-linearity
    if(tm > 5):
        return m.pro_mode_run[tm, stf, sit, pro] >= \
               (1 - m.pro_mode_run[tm - 1, stf, sit, pro] * m.pro_mode_run[tm - 2, stf, sit, pro]
                * m.pro_mode_run[tm - 3, stf, sit, pro]) * m.pro_mode_run[tm - 1, stf, sit, pro]
    else:
        return pyomo.Constraint.Skip