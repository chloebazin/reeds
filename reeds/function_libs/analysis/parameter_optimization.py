import warnings
from typing import List, Dict, Union

import numpy as np
import pandas as pd
from pygromos.files import imd, repdat

import reeds.function_libs.visualization.parameter_optimization_plots
import reeds.function_libs.visualization.re_plots
from reeds.function_libs.optimization import eds_energy_offsets as eoff, eds_s_values as sopt_wrap
from reeds.function_libs.optimization.src import sopt_Pathstatistic as parseS

# when we switch to the new offsets: 
import reeds.function_libs.optimization.new_energy_offsets as estimate
from reeds.function_libs.visualization.parameter_optimization_plots import plot_offsets_vs_s


def estimate_Eoff(ene_ana_trajs: List[pd.DataFrame],
                  Eoff: List[float],
                  s_values: List[float],
                  out_path: str,
                  temp: float = 298,
                  kb: float = 0.00831451,
                  pot_tresh: Union[float, List[float]] = 0.0,
                  frac_tresh: List[float] = [0.9],
                  convergence_radius: float = 0.05, max_iter: int = 12, take_last_n: int = None,
                  plot_title_prefix: str = "RE-EDS",
                  visualize: bool = True) -> Dict:
    """estimate_Eoff
    estimate Energy Offsets of REEDS sim.

    Parameters
    ----------
    Eoff :  List[float]
        list of energy offsets for each state
    s_values :  List[float]
        list of s-values for each replica
    ene_ana_trajs : List[pd.DataFrame]
        a list of pandas dataframes containing the energy data of each state eX
    out_path : str
        path of the eoff analysis directory
    temp : float, optional
        temperature (default 298)
    kb: float, optional
        Boltzmann constant (default 0.00831451)
    pot_tresh : float, optional
        threshold for counting an energy value as being in undersampling (default 0.0)
    frac_tresh : List[float], optional
        which fraction of the energies has to be below the pot_tresh for undersampling (default 0.9)
    convergence_radius : float, optional
        radius of convergence (default 0.05)
    max_iter : int, optional
        maximum number of iterations for eoff estimation (default 12)
    take_last_n : int, optional
        only use the last n energy values (default None)
    plot_title_prefix : str, optional
        prefix for the plot titles (default "RE-EDS")
    visualize: bool, optional
        create plots (default True)

    Returns
    -------
    Dict
        EOFF dictionary
    """

    # TODO: NEW AND BETTER?
    # calculate energy offsets:
    
    # Candide's new code:
    (all_eoffs, new_eoffs) = estimate.estimate_energy_offsets(ene_ana_trajs, initial_offsets= Eoff, s_values= s_values,
                                                               out_path = out_path + "/New_eoff_estimate.out", temp= temp,
                                                               pot_tresh= pot_tresh, frac_tresh= frac_tresh, trim_beg= 0.0
                                                              )
    
    plot_offsets_vs_s(all_eoffs, s_values=s_values,out_path = out_path + "/Eoffs_vs_s.png")
    
    # Candide : temporarily uncommented everything below

    #if take_last_n is not None:
    #    ene_ana_trajs = ene_ana_trajs[-take_last_n:]
    #    s_values = s_values[-take_last_n:]
    #    print("using Replicas: ", len(ene_ana_trajs), s_values)
    #if(isinstance(pot_tresh, float)):
    #    pot_tresh = [pot_tresh for x in range(len(Eoff))]
    #statistic = eoff.estEoff(ene_ana_trajs=ene_ana_trajs, out_path=out_path + "/Eoff_estimate.out", Temp=temp,
    #                         s_values=s_values, Eoff=Eoff, frac_tresh=frac_tresh, pot_tresh=pot_tresh,
    #                         convergenceradius=convergence_radius, kb=kb, max_iter=max_iter)
    
    # make plots and gather stuff!
    #if (visualize):
    #    eoff_per_replica = statistic[3]
    #    energy_offsets = statistic[0]

        # plott mean eoffs vs. sf
        #reeds.function_libs.visualization.parameter_optimization_plots.plot_peoe_eoff_vs_s(eoff_per_replica, energy_offsets, title=plot_title_prefix + " - Eoff/s",
        #                                                                                   out_path=out_path + "/" + plot_title_prefix + "_eoffs_vs_s.png")
    return new_eoffs


def energyOffset_time_convergence(ene_ana_trajs, out_dir: str, Eoff: List[float], s_values: List[float],
                                  steps: int = 10,
                                  temp: float = 298, kb: float = 0.00831451, pot_tresh: float = 0.0,
                                  frac_tresh: float = [0.9], convergence_radius: float = 0.05, max_iter=12,
                                  plot_title_prefix: str = "RE-EDS", visualize: bool = True):
    """


    """
    ene_traj = ene_ana_trajs[0]

    start_index, end_index = (min(ene_traj.index), max(ene_traj.index))
    step_size = (end_index - start_index) // steps
    time_step = ene_traj.time[1] - ene_traj.time[0]
    steps_range = range(step_size, end_index, step_size)

    time_statistic = {}
    for last_step in steps_range:
        # shorten data
        shortened_trajs = []
        for ene_traj in ene_ana_trajs:
            tmp_ene_traj = ene_traj.iloc[ene_traj.index < last_step]
            tmp_ene_traj.replicaID = ene_traj.replicaID
            shortened_trajs.append(tmp_ene_traj)
            print(len(tmp_ene_traj))

        # estm eoff
        statistic = eoff.estEoff(ene_ana_trajs=shortened_trajs, out_path=out_dir + "/Eoff_estimate_new.out",
                                 Temp=temp, s_values=s_values, Eoff=Eoff,
                                 frac_tresh=frac_tresh, pot_tresh=pot_tresh, convergenceradius=convergence_radius,
                                 kb=kb,
                                 max_iter=max_iter)

        time_statistic.update({last_step: statistic})

    state_time_dict = {"time_step": time_step}
    sorted_keys = sorted(time_statistic)
    last_steps = list(steps_range)
    for stateInd, (mean, std) in enumerate(time_statistic[sorted_keys[0]].offsets):
        state_time_dict.update({stateInd + 1: {"mean": [mean], "std": [std], "time": [time_step * last_steps[0]]}})

    for ene_traj_key in sorted_keys[1:]:
        ene_traj = time_statistic[ene_traj_key]
        for stateInd, (mean, std) in enumerate(ene_traj.offsets):
            state_time_dict[stateInd + 1]["mean"].append(mean)
            state_time_dict[stateInd + 1]["std"].append(std)
            state_time_dict[stateInd + 1]["time"].append(ene_traj_key * time_step)

    if (visualize):
        reeds.function_libs.visualization.parameter_optimization_plots.plot_peoe_eoff_time_convergence(state_time_dict,
                                                                                                       out_path=out_dir + "/" + plot_title_prefix + "_eoff_convergence.png")
    return state_time_dict


def optimize_s(in_file: str,
               add_s_vals: int,
               out_dir: str,
               title_prefix: str = "sOpt",
               state_weights=None,
               trial_range: (int or tuple) = None,
               with_skipped: bool = True,
               verbose: bool = True,
               run_NLRTO: bool = True,
               run_NGRTO: bool = False,
               in_imd: str = None) -> Dict:
    """optimize_s
    This function is doing the S-optimization for a RE-EDS simulation.

    Parameters
    ----------
    in_file : str
        input path to repdat-file
    add_s_vals : int
        number of s_values to be added
    out_dir : str
        output_directory path
    title_prefix : str, optional
        title prefix for plots (default sOpt)
    state_weights : List[float], optional
        weights for each individual endstate of eds potential (default None)
    trial_range : [int, tuple], optional
        range of trials (time dimension) (default None)
    with_skipped : bool , optional
        default True
    verbose : bool, optional
        verbose output (default True)
    run_NLRTO : bool, optional
        run N-Local Round Trip Optimizer (N-LRTO) (default True)
    run_NGRTO : bool, optional
        run Multistate Global Round-Trip Time Optimization (N-GRTO) (default False)
    in_imd : str, optional
        this path to an imd file is suggested to be used, as it increases the s_value accuracy (default None)

    Returns
    -------
    Dict
        s-values (original, N-LRTO optimized, N-GRTO optimized)
    """

    # do soptimisation
    if verbose:
        print("RUN sopt")
        print("\tRead in repdat: " + in_file)
    stat = parseS.generate_PathStatistic_from_file(in_file, trial_range=trial_range)

    if (in_imd != None):
        imd_file = imd.Imd(in_imd)
        svals = list(map(float, imd_file.REPLICA_EDS.RES))
        setattr(stat, "s_values", sorted(list(set(svals)), reverse=True))
        setattr(stat, "raw_s_values", sorted(svals, reverse=True))

    else:
        warnings.warn("Careful no imd given, the accuracy of repdat s_vals is very low!")

    if verbose: print("\n\tOptimize S-Dist")
    # NLRTO
    if (run_NLRTO):
        if verbose: print("\tNLRTO")
        new_svals_NLRTO, NLRTO = sopt_wrap.calc_NLRTO(stat, add_n_s=add_s_vals, state_weights=state_weights,
                                                      verbose=verbose)
    else:
        new_svals_NLRTO = []
        NLRTO = None

    # NGRTO
    if (run_NGRTO):
        if verbose: print("\tNGRTO")
        smin = min(stat.s_values)
        ds = float("0.0" + "".join(["0" for x in range(str(smin).count("0") + 1)]) + "1")
        new_svals_NGRTO, NGRTO = sopt_wrap.calc_NGRTO(stat, add_n_s=add_s_vals, state_weights=state_weights, ds=ds,
                                                      verbose=verbose)
    else:
        new_svals_NGRTO = []
        NGRTO = None

    if (with_skipped):
        data = {0: stat.raw_s_values, 1: new_svals_NLRTO, 2: new_svals_NGRTO}
    else:
        data = {0: stat.s_values, 1: NLRTO.opt_replica_parameters, 2: NGRTO.opt_replica_parameters}

    # output of svals NLRTO
    if (run_NLRTO):
        output_file = open(out_dir + "/" + title_prefix + "_NLRTO.out", "w")
        output_file.write(str(NLRTO))
        output_file.close()

    # output of svals NGRTO
    if (run_NGRTO):
        output_file = open(out_dir + "/" + title_prefix + "_NGRTO.out", "w")
        output_file.write(str(NGRTO))
        output_file.close()

    if verbose: print("Done!\n\n")

    return data


def get_s_optimization_transitions(out_dir: str,
                                   rep_dat: str,
                                   title_prefix: str,
                                   verbose: bool = True):
    """get_s_optimization_transitions
    This function visualized the replica transitions

    Parameters
    ----------
    out_dir : str
        path where the plots should be stored
    rep_dat : str
        path to the repdat file containing the replica transition history
    title_prefix : str
        title prefix for plots
    verbose : bool, optional
        verbose output (default True)

    Returns
    -------
    None
    """

    if verbose: print("Vizualise \n\t")
    if verbose: print("Plot output in: " + out_dir)

    # visualize transitions
    repdat_file = repdat.Repdat(rep_dat)
    old_svals = list(map(float, repdat_file.system.s))

    # print(list(repdat_file.keys()))
    if verbose: print("\t transition plots ")
    transitions = repdat_file.get_replica_traces()
    if verbose: print("\t\t draw replica traces ")
    reeds.function_libs.visualization.re_plots.plot_replica_transitions(transitions, s_values=old_svals, out_path=out_dir + "/transitions.png",
                                                                        title_prefix=title_prefix)
    reeds.function_libs.visualization.re_plots.plot_replica_transitions(transitions, s_values=old_svals, out_path=out_dir + "/transitions_cutted.png",
                                                                        title_prefix=title_prefix, cut_1_replicas=True)
    reeds.function_libs.visualization.re_plots.plot_replica_transitions(transitions, s_values=old_svals, out_path=out_dir + "/transitions_cutted_250.png",
                                                                        title_prefix=title_prefix, cut_1_replicas=True, xBond=(0, 250))
    # single trace replica
    if verbose: print("\t\t draw single replica trace ")
    for replica in range(1, len(repdat_file.system.s) + 1):  # future: change to ->repdat_file.num_replicas
        single_transition_trace = transitions.loc[transitions.replicaID == replica]
        reeds.function_libs.visualization.re_plots.plot_replica_transitions_min_states(single_transition_trace, s_values=old_svals,
                                                                                       out_path=out_dir + "/transitions_trace_" + str(replica) + ".png",
                                                                                       title_prefix=title_prefix,
                                                                                       cut_1_replicas=True)
        # vis.plot_state_transitions_min_states(single_transition, s_values=old_svals,
        #                           out_path=out_path + "/transitions_trace_" + str(replica) + "_250t.png",
        #                           title_prefix=title_prefix,
        #                           cut_1_replicas=True, xBond=(0, 250))


def get_s_optimization_roundtrips_per_replica(data: Dict[int, Dict[str,List[float]]],
                                              max_pos: int,
                                              min_pos: int,
                                              repOffsets: int = 0) -> dict:
    """get_s_optimization_roundtrips_per_replica
    This function calculates the roundtrips of a replica

    Parameters
    ----------
    data : Dict[int, Dict[str,List[float]]]
        transition traces dictionary from Repdat class
    max_pos : int
        maximum position of the replica
    min_pos : int
        minimum position of the replica
    repOffsets : int, optional
        skip multiple replicas with s = 1

    Returns
    -------
    Dict
        replica statistics, with udated roundtrips information
    """
    replicas = np.unique(data.replicaID)[repOffsets:]
    max_pos, min_pos = min_pos, max_pos

    replica_stats = {}
    for replica in replicas:
        df = data.loc[data.replicaID == replica]
        extreme_pos = df.loc[(df.position == min_pos) | (df.position == max_pos)]

        roundtrip_counter = 0
        durations = []
        if (len(extreme_pos) > 0):
            lastExtreme = extreme_pos.iloc[0].position
            lastTrial = extreme_pos.iloc[0].trial
            for row_ind, extr in extreme_pos.iterrows():
                if (extr.position != lastExtreme):
                    roundtrip_counter += 1
                    durations.append(extr.trial - lastTrial)

                    lastExtreme = extr.position
                    lastTrial = extr.trial
        replica_stats.update({replica: {"roundtrips": roundtrip_counter, "durations": durations}})

    return replica_stats


def get_s_optimization_roundtrip_averages(stats: dict):
    """get_s_optimization_roundtrip_averages
    This function calculates the roundtrip averages

    Parameters
    ----------
    stats : dict
        replica statistics

    Returns
    -------
    nReplicaRoundtrips : List
        list of replicas with at least one roundtrip
    avg_numberOfRoundtrips : List[float]
        list of average number of roundtrips per replica
    avg_roundtrips : List[float]
        list of average roundtrip duration per replica

    Returns
    -------
    None
    """
    nReplicasRoundtrips = np.sum([1 for stat in stats if (stats[stat]["roundtrips"] > 0)])
    numberOfRoundtrips = [stats[stat]["roundtrips"] for stat in stats]
    avg_numberOfRoundtrips = np.mean(numberOfRoundtrips)

    roundtrip_durations = [np.mean(stats[stat]["durations"]) for stat in stats if (len(stats[stat]["durations"]) > 0)]
    avg_roundtrips = np.inf if (np.mean(roundtrip_durations) == 0 or len(roundtrip_durations) == 0) else np.mean(
        roundtrip_durations)

    print("Number of roundtrips per replica: ", numberOfRoundtrips)
    print("Avg. Roundtrips per replica: ", roundtrip_durations)
    print()
    return nReplicasRoundtrips, avg_numberOfRoundtrips, avg_roundtrips
