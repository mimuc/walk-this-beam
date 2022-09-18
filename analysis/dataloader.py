# Copyright © 2022 LMU Munich Media Informatics Group. All rights reserved.
# Written by Changkun Ou <https://changkun.de>.
#
# Use of this source code is governed by a GNU GPLv3 license that
# can be found in the LICENSE file.

# This script provides a simple data loader for the analysis of the
# data collected from the "Walk this Beam" experiment.

from typing import List, Tuple
from datetime import datetime, timedelta
import glob
import numpy as np
import pandas as pd


class Participant:
    """P is a participant dataset that provide multiple methods
    for fetching corresponding data frame.
    """

    def __init__(self, user_id: int, meta: pd.DataFrame) -> None:
        self.data_folder = '../data'
        self.user_id = user_id
        self.meta = meta
        self.motions = {
            'beam_s': 'motion_BeamStart_Target',
            'beam_e': 'motion_BeamEnd_Target',
            'foot_l': 'motion_LeftFoot_Target',
            'foot_r': 'motion_RightFoot_Target',
            'hand_l': 'motion_LeftHand_Target',
            'hand_r': 'motion_RightHand_Target',
            'head':   'motion_Head_Target',
            'pelvis': 'motion_Pelvis_Target',
            'sphere': 'motion_Sphere Kopf(Clone)',
        }

    def __glob_sensor_by(self, user_id: int, method: str, tide: str, type: str) -> List[str]:
        return glob.glob(f'{self.data_folder}/{user_id}/{user_id}_{method}_{tide}_*_{type}*.csv')

    def by(self, method: str, tide: str, datatyp: str) -> List[str]:
        """by searches a list of file paths with respect to the given
        experiment method, the height of tide, and the type of data

        Args:
            method (str): experiment method
            tide (str): height of tide
            datatyp (str): type of data, such as ECG, EDA, and motion.

        Returns:
            List[str]: a list of file paths
        """
        return self.__glob_sensor_by(self.user_id, method, tide, datatyp)

    def ecg_raw(self, method: str, tide: str) -> pd.DataFrame:
        """ecg_raw returns a pd.DataFrame of the ECG data corresponding
        to the given experiment method, and the height of tide.

        Args:
            method (str): experiment method
            tide (str): height of tide

        Returns:
            pd.DataFrame: ECG data frame.
        """
        fpath = self.by(method, tide, 'ECG')[0]
        return pd.read_csv(fpath)

    def ecg(self, method: str, tide: str, lap: int) -> pd.DataFrame:
        df_ecg = self.ecg_raw(method, tide)
        laps = self.lap_state(method, tide)
        return df_ecg[df_ecg['unixTime'].between(
            laps[lap][0], laps[lap][1])]

    def eda_raw(self, method: str, tide: str) -> pd.DataFrame:
        """eda_raw returns a pd.DataFrame of the EDA data corresponding
        to the given experiment method, and the height of tide.

        Args:
            method (str): experiment method
            tide (str): height of tide

        Returns:
            pd.DataFrame: EDA data frame.
        """
        fpath = self.by(method, tide, 'EDA')[0]
        return pd.read_csv(fpath)

    def eda(self, method: str, tide: str, lap: int) -> pd.DataFrame:
        df_eda = self.eda_raw(method, tide)
        laps = self.lap_state(method, tide)
        df_eda_lap = df_eda[df_eda['unixTime'].between(
            laps[lap][0], laps[lap][1])]
        return df_eda_lap

    def lap_state(self, method: str, tide: str) -> List[List[datetime]]:
        fpath = self.by(method, tide, 'state')[0]
        lap_state = pd.read_csv(fpath, delimiter=';')
        laps = [
            [
                lap_state[lap_state['state'] ==
                          'S1HasHitBeam'].timestamp.values[0],
                lap_state[lap_state['state'] ==
                          'S1HasHitEnd'].timestamp.values[0],
            ],
            [
                lap_state[lap_state['state'] ==
                          'S2HasHitBeam'].timestamp.values[0],
                lap_state[lap_state['state'] ==
                          'S2HasHitStart'].timestamp.values[0],
            ],
            [
                lap_state[lap_state['state'] ==
                          'S3HasHitBeam'].timestamp.values[0],
                lap_state[lap_state['state'] ==
                          'S3HasHitEnd'].timestamp.values[0],
            ],
            [
                lap_state[lap_state['state'] ==
                          'S4HasHitBeam'].timestamp.values[0],
                lap_state[lap_state['state'] ==
                          'S4HasHitStart'].timestamp.values[0],
            ]
        ]
        return laps

    def laps(self, method: str, tide: str) -> pd.DataFrame:
        """laps can be deduced from lap_state, for example:

        for j in dataset.user_ids:
            p = dataset.load_participant(j)
            for m in ['NoInstructions', 'Imitation', 'Gamification']:
                for t in ['HighTide', 'LowTide']:
                    laps = p.lap_state(m, t)
                    laps2 = p.laps(m, t)
                    time = [laps[i][1] - laps[i][0] for i in range(0, 4)]
                    t1 = np.array(time)
                    t2 = laps2['time'].to_numpy(dtype=np.int64)
                    print(j, m, t, np.subtract(t1, t2))
        """
        fpath = self.by(method, tide, 'laps')[0]
        return pd.read_csv(fpath, delimiter=';')

    def falls(self, method: str, tide: str) -> pd.DataFrame:
        """falls returns a data frame that contains fall durations.
        Usage example:

        dataset = Dataset()
        fall = dataset[0].falls(dataset.methods[0], dataset.tides[0])
        print(fall)
        """
        fpath = self.by(method, tide, 'falls')[0]
        fall = pd.read_csv(fpath, delimiter=';')
        starts = []
        ends = []
        durations = []

        for v in fall['timestamp'].values:
            fall_end = v
            fall_duration = timedelta(milliseconds=fall['duration'].values[0])
            fall_start = round(datetime.timestamp(
                datetime.fromtimestamp(fall_end/1000) - fall_duration)*1000)

            starts.append(fall_start)
            ends.append(fall_end)
            durations.append(fall_duration)

        fall['timestamp_start'] = np.array(starts)
        fall['timestamp_end'] = np.array(ends)
        fall['timestamp_duration'] = np.array(durations)

        self.all_falls = fall[[
            'timestamp_start', 'timestamp_end', 'timestamp_duration', 'position', 'round']]
        return self.all_falls

    def fall(self, method: str, tide: str, lap: int) -> pd.DataFrame:
        """falls returns a data frame that contains fall durations of a lap.
        Usage example:

        dataset = Dataset()
        fall = dataset[0].falls(dataset.methods[0], dataset.tides[0], 0)
        print(fall)
        """
        df = self.falls(method, tide)
        return df[df['round'] == lap]

    def steps(self, method: str, tide: str) -> pd.DataFrame:
        fpath = self.by(method, tide, 'steps')[0]
        return pd.read_csv(fpath, delimiter=';')

    def raw_motion(self, method: str, tide: str) -> pd.DataFrame:
        df = pd.DataFrame()
        for abbr in self.motions:
            # Note: only gamification have sphere data
            if abbr == 'sphere' and method != 'game':
                continue

            timestamp = pd.read_csv(self.by(method, tide, self.motions[abbr])[0])[
                'timestamp']
            df['timestamp'] = timestamp

            df[f'{abbr}_posX'] = pd.read_csv(
                self.by(method, tide, self.motions[abbr])[0])['posX']
            df[f'{abbr}_posY'] = pd.read_csv(
                self.by(method, tide, self.motions[abbr])[0])['posY']
            df[f'{abbr}_posZ'] = pd.read_csv(
                self.by(method, tide, self.motions[abbr])[0])['posZ']
            df[f'{abbr}_rotX'] = pd.read_csv(
                self.by(method, tide, self.motions[abbr])[0])['rotX']
            df[f'{abbr}_rotY'] = pd.read_csv(
                self.by(method, tide, self.motions[abbr])[0])['rotY']
            df[f'{abbr}_rotZ'] = pd.read_csv(
                self.by(method, tide, self.motions[abbr])[0])['rotZ']
        return df

    def motion(self, method: str, tide: str, lap: int) -> pd.DataFrame:
        df_motion = self.raw_motion(method, tide)
        laps = self.lap_state(method, tide)
        df_motion_lap = df_motion[df_motion['timestamp'].between(
            laps[lap][0], laps[lap][1])]
        return df_motion_lap

    def ipq(self, tide: str) -> Tuple[pd.DataFrame, int]:
        """The iGroup Presence Questionnaire. See for more information:
        https://therealitydemo.github.io/

        Args:
            condition (str): HL or LH

        Returns:
            Tuple[pd.DataFrame, int]: the corresponding data frame and if it is measured in the middle or the end of the study.
        """
        f = glob.glob(
            f'{self.data_folder}/{self.user_id}/questionnaireID_IPQ*{tide}*.csv')
        isMid = False
        if 'mid' in f[0]:
            isMid = True
        df = pd.read_csv(f[0], delimiter=';')
        return df['Answer'], isMid

    def nasa_tlx(self, tide: str, method: str):
        """The NASATLX scale

        Args:
            tide (str): HL or LH
            method (str): none, imit, or game

        Returns:
            pd.DataFrame: the questionaire data.
        """
        if method == 'NoInstructions':
            method = 0
        elif method == 'Imitation':
            method = 1
        elif method == 'Gamification':
            method = 2

        f = glob.glob(
            f'{self.data_folder}/{self.user_id}/questionnaireID_NASA*{tide}_{method}*.csv')
        return pd.read_csv(f[0], delimiter=';')['Answer']

    def paces(self, tide_order: str, method: str):
        if method == 'NoInstructions':
            method = 0
        elif method == 'Imitation':
            method = 1
        elif method == 'Gamification':
            method = 2

        f = glob.glob(
            f'{self.data_folder}/{self.user_id}/questionnaireID_PACES*{tide_order}_{method}*.csv')
        return pd.read_csv(f[0], delimiter=';')['Answer']

    def full_experiment(self) -> pd.DataFrame:
        all = pd.DataFrame(columns=[
            'user_id', 'method', 'timestamp', 'tide', 'age', 'gender', 'occupation', 'blurred', 'game_exp', 'vr_exp', 'training_need',
        ])
        age = self.meta.age.tolist()[0]
        gender = self.meta.gender.tolist()[0]
        occupation = self.meta.occupation.tolist()[0]
        blurred = self.meta.blurred_preceiving.tolist()[0]
        game_exp = self.meta.game_experience.tolist()[0]
        vr_exp = self.meta.vr_experience.tolist()[0]
        training_need = self.meta.training_need.tolist()[0]
        for m in ['NoInstructions', 'Imitation', 'Gamification']:
            for t in ['LowTide', 'HighTide']:
                motions, lens = self.raw_motion(m, t)
                all = all.append({
                    'user_id':       self.user_id,
                    'method':        m,
                    'tide':          t,
                    'timestamp':     lens['beam_e'],
                    'age':           age,
                    'gender':        gender,
                    'occupation':    occupation,
                    'blurred':       blurred,
                    'game_exp':      game_exp,
                    'vr_exp':        vr_exp,
                    'training_need': training_need,
                }, ignore_index=True)
        return all


class Dataset:
    def __init__(self) -> None:
        self.data_folder = '../data'
        self.user_ids = [i for i in range(10, 29)]
        self.tides = ['LH', 'HL']
        self.bios = ['ECG', 'EDA']
        self.methods = ['NoInstructions', 'Imitation', 'Gamification']
        self.tides = ['LowTide', 'HighTide']
        self.meta = pd.read_csv(f'{self.data_folder}/meta.csv')

    def load_participant(self, user_id: int) -> Participant:
        return Participant(user_id, self.meta[self.meta.user_id == user_id])

    def __getitem__(self, index: int):
        if index < 0 or index > 19:
            raise Exception('out of index!')
        return self.load_participant(index+10)
