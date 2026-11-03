"""Joint rules. Ranges in degrees: measured rows from the CDC's Joint Range of Motion Study (Soucie 2011), ages 20-44, by sex; others declared and marked."""

CDC = {  # motion: (female, male), mean
    "shoulder_flexion": (172.0, 168.8),
    "elbow_flexion": (150.0, 144.6),
    "elbow_extension": (4.7, 0.8),
    "hip_flexion": (133.8, 130.4),
    "hip_extension": (18.1, 17.4),
    "knee_flexion": (141.9, 137.7),
    "knee_extension": (1.6, 1.0),
    "ankle_dorsiflexion": (13.8, 12.7),
    "ankle_plantarflexion": (62.1, 54.6),
}
DECLARED = {  # no measured source read yet, textbook-order values, each one opens a question in the task file
    "shoulder_extension": 50.0,
    "shoulder_abduction": 170.0,
    "hip_abduction": 45.0,
    "hip_adduction": 25.0,
    "wrist_flexion": 75.0,
    "wrist_extension": 70.0,
    "finger_flexion": 90.0,
    "spine_flexion_per_segment": 12.0,
    "neck_flexion_per_segment": 15.0,
}
# Rotations about the rest pose's X axis (+X is the body's left): (rig bone stem, minus limit, plus limit) by sex. Signs: hip flexion swings the leg to -Y, which is a negative rotation.
SEX = {"female": 0, "male": 1}


def limits(sex):
    i = SEX[sex]
    c = lambda k: CDC[k][i]
    return {
        "thigh": (-c("hip_flexion"), c("hip_extension")),
        "shin": (-c("knee_extension"), c("knee_flexion")),
        "foot": (-c("ankle_dorsiflexion"), c("ankle_plantarflexion")),
        "upper_arm": (-c("shoulder_flexion"), DECLARED["shoulder_extension"]),
    }


def elbow_limits(sex):
    i = SEX[sex]
    return (-CDC["elbow_extension"][i], CDC["elbow_flexion"][i])


# Ribs: axis blend between pump handle (upper ribs, left-right axis) and bucket handle (lower ribs, front-back axis), degrees at full deep breath.
def rib_rule(index):
    """(axis weight towards bucket handle, degrees at a deep breath). Declared, checked only through the chest expansion it gives."""
    bucket = min(max((index - 1) / 9.0, 0.0), 1.0)
    return bucket, 9.0 if index <= 10 else 3.0
