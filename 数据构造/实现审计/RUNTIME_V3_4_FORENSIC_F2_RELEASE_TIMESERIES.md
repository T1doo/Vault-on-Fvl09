# runtime-v3_4 F2 release timeseries forensic

- design_version: `controlled_multi_future_f1_f4_v1_2`
- implementation_version: `controlled_multi_future_runtime_v3_4`
- formal_data: `false`
- stage0_data: `false`
- output_sha256: `2919e9844ae386f1a65faa58c4d975ad7e21435ee627eb190b3e9bd46306dab3`

## 机器可读正文

```json
{
  "derived_metric_formula": {
    "contact": "physical iff impulse_norm_sum > 1e-10 or any signed separation <= 0; missing signal fails closed",
    "opening_projection_margin": "minimum signed margin on box-local axes 0 and 2",
    "opening_safety_envelope": "can geometry center inside the cavity opening rectangle and can OBB projection still overlaps that rectangle; this is not final full-OBB inside",
    "relative_orientation": "sign-invariant quaternion angular error in box frame",
    "speed": "Euclidean norm of pose-derived 250 Hz linear/angular velocity",
    "trend": "ordinary least-squares slope versus trace frame index",
    "true_cavity_margin": "minimum signed margin of all can OBB corners to all six cavity planes"
  },
  "derived_metrics": {
    "final_opening_center_inside": true,
    "final_opening_center_signed_margin_m": 0.020477068488896633,
    "final_opening_projection_inside": false,
    "final_opening_projection_overlap_signed_m": 0.05804087656140766,
    "final_opening_projection_overlaps": true,
    "final_opening_projection_signed_margin_m": -0.017086739583614396,
    "final_true_cavity_obb": false,
    "final_true_cavity_signed_margin_m": -0.019866570824753686,
    "first_no_physical_finger_contact_trace_row": 2192,
    "last_10_continuous_box_contact": true,
    "last_10_fingers_detached": true,
    "last_50_angular_speed_slope_rps_per_frame": -0.0009042668901310582,
    "last_50_linear_speed_slope_mps_per_frame": -2.1552782035211474e-05,
    "last_50_maximum_angular_speed_rps": 0.7239935887344399,
    "last_50_maximum_linear_speed_mps": 0.016602695290689955,
    "last_50_opening_margin_slope_m_per_frame": 7.019521380949833e-05,
    "last_50_true_cavity_margin_slope_m_per_frame": 3.693261511624728e-05,
    "maximum_angular_speed_rps": 9.968249636660413,
    "maximum_linear_speed_mps": 1.5019701486330175,
    "partial_window_row_count": 351
  },
  "design_version": "controlled_multi_future_f1_f4_v1_2",
  "forensic_conclusion": {
    "classification": "revision9_gate_conflated_release_safety_with_final_inside_success",
    "evidence": {
      "box_contact_continuous": true,
      "final_angular_stability_not_yet_satisfied": true,
      "final_true_cavity_not_yet_satisfied": true,
      "finger_disengagement_complete": true,
      "opening_safety_envelope_at_gate": true,
      "strict_opening_projection_not_yet_inside": true
    },
    "next_frozen_test": "safety gate permits full-open without requiring final cavity/stability; final success is evaluated only after exactly 250 settle frames"
  },
  "formal_data": false,
  "implementation_strategy": "diagnosis_first_multi_gpu_convergence",
  "implementation_version": "controlled_multi_future_runtime_v3_4",
  "output_sha256": "2919e9844ae386f1a65faa58c4d975ad7e21435ee627eb190b3e9bd46306dab3",
  "output_sha256_scope": "canonical JSON of this artifact with output_sha256 removed",
  "schema_version": "cmf_runtime_v3_4_forensic_f2_release_timeseries_v1",
  "selected_fields": [
    "step_index",
    "timestamp",
    "role_object_pose__main_can",
    "role_object_linear_velocity__main_can",
    "role_object_angular_velocity__main_can",
    "role_object_pose__box",
    "realized_left_gripper_joint_qpos/qvel/qf",
    "left_gripper_joint_drive_target",
    "contact_pairs_json"
  ],
  "selected_row_indices": {
    "count": 351,
    "end_inclusive": 2321,
    "event_markers": {
      "canonical_prefix_end": 1295,
      "canonical_prefix_replay_start": 0,
      "canonical_prefix_settling_end": 1345,
      "canonical_prefix_settling_start": 1295,
      "f2_inside_balanced_preload_hold_end": 2321,
      "f2_inside_balanced_preload_start": 1971,
      "trace_start": 0
    },
    "start": 1971
  },
  "source_manifest_path": "数据构造/实现审计/F2_ROOT_RUNTIME_V3_3_REVISION9_FAILURE_EVIDENCE_MANIFEST_20260830.json",
  "source_manifest_sha256": "2092ff110f0bba87b61c40a267b829913cbabe27e09a5e9dc74e8bd75fc778be",
  "source_raw_path": "数据构造/实现审计/probe_outputs/nonformal_runtime_v3_3_f2_root_seed20260829_revision9_run1_gpu0/root/branches/F2-inside/partial_trace_source.npz",
  "source_raw_sha256": "75ac8f9863ff49549703dfe11acda43e9ace81e134e72298309beccf99c97e48",
  "source_receipt_path": "数据构造/实现审计/probe_outputs/nonformal_runtime_v3_3_f2_root_seed20260829_revision9_run1_gpu0/root/branches/F2-inside/receipt.json",
  "source_receipt_sha256": "957d1fa61f2330a2fef97d580566c31e6406dfe567b53f1d1a916cf7a1964c02",
  "stage0_authorized": false,
  "stage0_data": false,
  "timeseries": [
    {
      "actual_left_finger_qpos_m": [
        0.023574866354465485,
        0.02150568924844265
      ],
      "angular_speed_rps": 0.014094058658816114,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000743768578326226,
        0.16658982948453083,
        0.0010505797173228082
      ],
      "can_pose": [
        -0.29155659675598145,
        -0.15337501466274261,
        0.9431151747703552,
        0.005604051519185305,
        0.6993917226791382,
        0.045792993158102036,
        0.7132482528686523
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0,
      "can_relative_translation_from_partial_start_m": [
        0.0,
        0.0,
        0.0
      ],
      "can_to_box_relative_orientation_rad": 1.4990328212560478,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009999999776482582,
        -0.009999999776482582
      ],
      "left_finger_qf_audit_only": [
        6.8042778968811035,
        -6.804299831390381
      ],
      "left_finger_qvel_mps": [
        -0.0014847640413790941,
        0.0008633078541606665
      ],
      "linear_speed_mps": 0.0023002904839392164,
      "local_corner_max_m": [
        0.051556642657934054,
        0.20314372680654535,
        0.03704203614064672
      ],
      "local_corner_min_m": [
        -0.05304417981458648,
        0.1300359321625163,
        -0.0349408767060011
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07671844298584812,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11270989940917203,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025201954943409113,
      "step_index": 1971,
      "timestamp_seconds": 7.884000374469906,
      "trace_row": 1971,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.098378331493044,
      "vertical_lower_margin_m": 0.10827053684901494,
      "vertical_upper_margin_m": -0.098378331493044
    },
    {
      "actual_left_finger_qpos_m": [
        0.023575961589813232,
        0.021504545584321022
      ],
      "angular_speed_rps": 0.013787867380107226,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007393280528683877,
        0.1665867880064017,
        0.0010447366250142531
      ],
      "can_pose": [
        -0.29156428575515747,
        -0.15337061882019043,
        0.9431129097938538,
        0.005583707243204117,
        0.6993795037269592,
        0.04580087587237358,
        0.7132598757743835
      ],
      "can_relative_orientation_from_partial_start_rad": 5.5151466326900374e-05,
      "can_relative_translation_from_partial_start_m": [
        4.395842552185059e-06,
        -2.2649765014648438e-06,
        -7.68899917602539e-06
      ],
      "can_to_box_relative_orientation_rad": 1.4990519690964113,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009999999776482582,
        -0.009999999776482582
      ],
      "left_finger_qf_audit_only": [
        6.788505554199219,
        -6.78853702545166
      ],
      "left_finger_qvel_mps": [
        -0.0015787510201334953,
        0.0009546292130835354
      ],
      "linear_speed_mps": 0.002285473838802086,
      "local_corner_max_m": [
        0.051561752768586266,
        0.20314098729318897,
        0.037039097460059955
      ],
      "local_corner_min_m": [
        -0.05304040887432304,
        0.13003258871961443,
        -0.03494962421003145
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07672428607815668,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11271864691320238,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02520572588367255,
      "step_index": 1972,
      "timestamp_seconds": 7.888000374659896,
      "trace_row": 1972,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09837559197968761,
      "vertical_lower_margin_m": 0.10826719340611307,
      "vertical_upper_margin_m": -0.09837559197968761
    },
    {
      "actual_left_finger_qpos_m": [
        0.023577352985739708,
        0.021504204720258713
      ],
      "angular_speed_rps": 0.01575184429793345,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007348256807822029,
        0.1665837451101696,
        0.0010389238492758412
      ],
      "can_pose": [
        -0.29157230257987976,
        -0.15336616337299347,
        0.9431108832359314,
        0.0055588847026228905,
        0.6993669867515564,
        0.04580960050225258,
        0.7132718563079834
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00011806490837304764,
      "can_relative_translation_from_partial_start_m": [
        8.851289749145508e-06,
        -4.291534423828125e-06,
        -1.570582389831543e-05
      ],
      "can_to_box_relative_orientation_rad": 1.4990764978777724,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009837298654019833,
        -0.009837298654019833
      ],
      "left_finger_qf_audit_only": [
        6.788281440734863,
        -6.78831148147583
      ],
      "left_finger_qvel_mps": [
        -0.0014654624974355102,
        0.0009927826467901468
      ],
      "linear_speed_mps": 0.0023482362661203003,
      "local_corner_max_m": [
        0.05156699593908831,
        0.20313804055163032,
        0.03703657214229694
      ],
      "local_corner_min_m": [
        -0.05303664730065272,
        0.13002944966870889,
        -0.03495872444374526
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07673009885389509,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11272774714691619,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025209487457342875,
      "step_index": 1973,
      "timestamp_seconds": 7.892000374849886,
      "trace_row": 1973,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09837264523812896,
      "vertical_lower_margin_m": 0.10826405435520753,
      "vertical_upper_margin_m": -0.09837264523812896
    },
    {
      "actual_left_finger_qpos_m": [
        0.023577101528644562,
        0.0215054452419281
      ],
      "angular_speed_rps": 0.023617733482307952,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007268744978419783,
        0.16657964552254556,
        0.0010277916788148378
      ],
      "can_pose": [
        -0.2915871739387512,
        -0.15335823595523834,
        0.9431092739105225,
        0.005512590520083904,
        0.6993691325187683,
        0.04581841826438904,
        0.7132694721221924
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0001997210012274986,
      "can_relative_translation_from_partial_start_m": [
        1.677870750427246e-05,
        -5.900859832763672e-06,
        -3.057718276977539e-05
      ],
      "can_to_box_relative_orientation_rad": 1.4991317420172456,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009674597531557083,
        -0.009674597531557083
      ],
      "left_finger_qf_audit_only": [
        6.788053512573242,
        -6.788079261779785
      ],
      "left_finger_qvel_mps": [
        -0.000758283887989819,
        0.00032505186391063035
      ],
      "linear_speed_mps": 0.00423225093770441,
      "local_corner_max_m": [
        0.05157569299449788,
        0.20313129000787244,
        0.037028929224535656
      ],
      "local_corner_min_m": [
        -0.053029441990181836,
        0.13002800103721868,
        -0.03497334586690598
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0767412310243561,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11274236857007691,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025216692767813756,
      "step_index": 1974,
      "timestamp_seconds": 7.8960003750398755,
      "trace_row": 1974,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09836589469437108,
      "vertical_lower_margin_m": 0.10826260572371732,
      "vertical_upper_margin_m": -0.09836589469437108
    },
    {
      "actual_left_finger_qpos_m": [
        0.023577874526381493,
        0.021505514159798622
      ],
      "angular_speed_rps": 0.022697361496850057,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007210262433736403,
        0.16657776004135538,
        0.0010183283626470918
      ],
      "can_pose": [
        -0.2916005849838257,
        -0.1533525288105011,
        0.9431084394454956,
        0.005474615842103958,
        0.6993594169616699,
        0.045839715749025345,
        0.7132778763771057
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0002888445962102133,
      "can_relative_translation_from_partial_start_m": [
        2.2485852241516113e-05,
        -6.735324859619141e-06,
        -4.398822784423828e-05
      ],
      "can_to_box_relative_orientation_rad": 1.4991580738276025,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009511896409094334,
        -0.009511896409094334
      ],
      "left_finger_qf_audit_only": [
        6.788167953491211,
        -6.788179397583008
      ],
      "left_finger_qvel_mps": [
        -0.000986010069027543,
        0.00046927077346481383
      ],
      "linear_speed_mps": 0.0036496912769822007,
      "local_corner_max_m": [
        0.05158332778916702,
        0.20312913593334847,
        0.037024209745158965
      ],
      "local_corner_min_m": [
        -0.0530253802759143,
        0.1300263841493623,
        -0.03498755301986478
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07675069434052384,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11275657572303571,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02522075448208129,
      "step_index": 1975,
      "timestamp_seconds": 7.900000375229865,
      "trace_row": 1975,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09836374061984711,
      "vertical_lower_margin_m": 0.10826098883586094,
      "vertical_upper_margin_m": -0.09836374061984711
    },
    {
      "actual_left_finger_qpos_m": [
        0.023579128086566925,
        0.021505150943994522
      ],
      "angular_speed_rps": 0.01875829551444138,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007151655524891276,
        0.16657502912626865,
        0.0010096891095083826
      ],
      "can_pose": [
        -0.2916121184825897,
        -0.1533467024564743,
        0.9431074261665344,
        0.005439729429781437,
        0.6993514895439148,
        0.04584820568561554,
        0.7132853269577026
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00036355662086642073,
      "can_relative_translation_from_partial_start_m": [
        2.8312206268310547e-05,
        -7.748603820800781e-06,
        -5.552172660827637e-05
      ],
      "can_to_box_relative_orientation_rad": 1.4991974494308362,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009349195286631584,
        -0.009349195286631584
      ],
      "left_finger_qf_audit_only": [
        6.787990093231201,
        -6.788014888763428
      ],
      "left_finger_qvel_mps": [
        -0.0012400997802615166,
        0.0007253433577716351
      ],
      "linear_speed_mps": 0.0032403193638913057,
      "local_corner_max_m": [
        0.051589909315879756,
        0.20312540794232392,
        0.03701912419297626
      ],
      "local_corner_min_m": [
        -0.05302024042085801,
        0.13002465031021337,
        -0.034999745973959495
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07675933359366255,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11276876867713043,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02522589433713758,
      "step_index": 1976,
      "timestamp_seconds": 7.904000375419855,
      "trace_row": 1976,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09836001262882256,
      "vertical_lower_margin_m": 0.10825925499671202,
      "vertical_upper_margin_m": -0.09836001262882256
    },
    {
      "actual_left_finger_qpos_m": [
        0.02358010970056057,
        0.02150500938296318
      ],
      "angular_speed_rps": 0.017899986528243247,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007093452676272538,
        0.1665725652466099,
        0.001001409413307841
      ],
      "can_pose": [
        -0.2916230261325836,
        -0.1533408910036087,
        0.9431068301200867,
        0.005405776668339968,
        0.6993443369865417,
        0.045853596180677414,
        0.7132923007011414
      ],
      "can_relative_orientation_from_partial_start_rad": 0.000434378850442123,
      "can_relative_translation_from_partial_start_m": [
        3.412365913391113e-05,
        -8.344650268554688e-06,
        -6.642937660217285e-05
      ],
      "can_to_box_relative_orientation_rad": 1.4992397074495418,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009186494164168835,
        -0.009186494164168835
      ],
      "left_finger_qf_audit_only": [
        6.787867546081543,
        -6.787897109985352
      ],
      "left_finger_qvel_mps": [
        -0.0012041840236634016,
        0.0006855106330476701
      ],
      "linear_speed_mps": 0.003093390833920418,
      "local_corner_max_m": [
        0.051596191832437355,
        0.20312175477771743,
        0.0370140724261227
      ],
      "local_corner_min_m": [
        -0.05301488236769186,
        0.13002337571550238,
        -0.03501125359950702
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07676761328986309,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11278027630267795,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02523125239030373,
      "step_index": 1977,
      "timestamp_seconds": 7.908000375609845,
      "trace_row": 1977,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09835635946421607,
      "vertical_lower_margin_m": 0.10825798040200102,
      "vertical_upper_margin_m": -0.09835635946421607
    },
    {
      "actual_left_finger_qpos_m": [
        0.023580927401781082,
        0.02150505967438221
      ],
      "angular_speed_rps": 0.015264553169020405,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007037744601810503,
        0.16656976848506466,
        0.000993034397008541
      ],
      "can_pose": [
        -0.2916340231895447,
        -0.15333542227745056,
        0.94310462474823,
        0.005381257738918066,
        0.6993365287780762,
        0.04586855322122574,
        0.7132990956306458
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0004938733677591882,
      "can_relative_translation_from_partial_start_m": [
        3.959238529205322e-05,
        -1.055002212524414e-05,
        -7.742643356323242e-05
      ],
      "can_to_box_relative_orientation_rad": 1.499255098926174,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.009023793041706085,
        -0.009023793041706085
      ],
      "left_finger_qf_audit_only": [
        6.787757396697998,
        -6.787782192230225
      ],
      "left_finger_qvel_mps": [
        -0.0013033252907916903,
        0.0008056820370256901
      ],
      "linear_speed_mps": 0.0031195540329563647,
      "local_corner_max_m": [
        0.051603016648598676,
        0.2031189969916143,
        0.03700896527555797
      ],
      "local_corner_min_m": [
        -0.05301056556896078,
        0.13002053997851504,
        -0.03502289648154089
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07677598830616239,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11279191918471182,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025235569189034815,
      "step_index": 1978,
      "timestamp_seconds": 7.912000375799835,
      "trace_row": 1978,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09835360167811293,
      "vertical_lower_margin_m": 0.10825514466501368,
      "vertical_upper_margin_m": -0.09835360167811293
    },
    {
      "actual_left_finger_qpos_m": [
        0.02358170598745346,
        0.021505240350961685
      ],
      "angular_speed_rps": 0.015127504804089984,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006982654567667945,
        0.1665673687651198,
        0.0009850029783508574
      ],
      "can_pose": [
        -0.29164448380470276,
        -0.1533299684524536,
        0.9431033134460449,
        0.005354529246687889,
        0.6993290185928345,
        0.045878347009420395,
        0.7133060693740845
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0005543326659499544,
      "can_relative_translation_from_partial_start_m": [
        4.5046210289001465e-05,
        -1.1861324310302734e-05,
        -8.788704872131348e-05
      ],
      "can_to_box_relative_orientation_rad": 1.4992808003989746,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.008861091919243336,
        -0.008861091919243336
      ],
      "left_finger_qf_audit_only": [
        6.787631034851074,
        -6.787660121917725
      ],
      "left_finger_qvel_mps": [
        -0.001206587185151875,
        0.0007259550620801747
      ],
      "linear_speed_mps": 0.002967408134842732,
      "local_corner_max_m": [
        0.0516093510316884,
        0.20311616576745606,
        0.03700399374244662
      ],
      "local_corner_min_m": [
        -0.05300588194522199,
        0.13001857176278353,
        -0.0350339877857449
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07678401972482007,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11280301048891583,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025240252812773603,
      "step_index": 1979,
      "timestamp_seconds": 7.9160003759898245,
      "trace_row": 1979,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0983507704539547,
      "vertical_lower_margin_m": 0.10825317644928217,
      "vertical_upper_margin_m": -0.0983507704539547
    },
    {
      "actual_left_finger_qpos_m": [
        0.023582248017191887,
        0.021505627781152725
      ],
      "angular_speed_rps": 0.0148589523647669,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006928141636689256,
        0.16656429355913527,
        0.0009771937979219936
      ],
      "can_pose": [
        -0.2916545569896698,
        -0.15332454442977905,
        0.9431015849113464,
        0.005327170714735985,
        0.6993221044540405,
        0.04588497057557106,
        0.7133126258850098
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0006135581031634472,
      "can_relative_translation_from_partial_start_m": [
        5.047023296356201e-05,
        -1.3589859008789062e-05,
        -9.796023368835449e-05
      ],
      "can_to_box_relative_orientation_rad": 1.4993117546821457,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.008698390796780586,
        -0.008698390796780586
      ],
      "left_finger_qf_audit_only": [
        6.787510395050049,
        -6.787534713745117
      ],
      "left_finger_qvel_mps": [
        -0.001323907868936658,
        0.0008437534561380744
      ],
      "linear_speed_mps": 0.0028926296085981197,
      "local_corner_max_m": [
        0.05161536425245472,
        0.2031123731045159,
        0.03699902858376558
      ],
      "local_corner_min_m": [
        -0.05300099257979257,
        0.13001621401375463,
        -0.035044640987921594
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07679182890524894,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11281366369109253,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02524514217820302,
      "step_index": 1980,
      "timestamp_seconds": 7.920000376179814,
      "trace_row": 1980,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09834697779101455,
      "vertical_lower_margin_m": 0.10825081870025327,
      "vertical_upper_margin_m": -0.09834697779101455
    },
    {
      "actual_left_finger_qpos_m": [
        0.023582560941576958,
        0.02150616981089115
      ],
      "angular_speed_rps": 0.016927381795583972,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006873421212784947,
        0.16656143726488104,
        0.0009695375687474028
      ],
      "can_pose": [
        -0.2916650176048279,
        -0.15331915020942688,
        0.9430997967720032,
        0.005297744646668434,
        0.6993141174316406,
        0.04589769244194031,
        0.7133200168609619
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0006810534472990688,
      "can_relative_translation_from_partial_start_m": [
        5.586445331573486e-05,
        -1.537799835205078e-05,
        -0.00010842084884643555
      ],
      "can_to_box_relative_orientation_rad": 1.499337389453459,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.008535689674317837,
        -0.008535689674317837
      ],
      "left_finger_qf_audit_only": [
        6.787386894226074,
        -6.787412166595459
      ],
      "left_finger_qvel_mps": [
        -0.0013436266453936696,
        0.0008804199751466513
      ],
      "linear_speed_mps": 0.002976150109007859,
      "local_corner_max_m": [
        0.05162190503253736,
        0.20310913577127598,
        0.0369948476856623
      ],
      "local_corner_min_m": [
        -0.05299658927509432,
        0.1300137387584861,
        -0.035055772548167496
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07679948513442353,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11282479525133843,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025249545482901273,
      "step_index": 1981,
      "timestamp_seconds": 7.924000376369804,
      "trace_row": 1981,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09834374045777462,
      "vertical_lower_margin_m": 0.10824834344498474,
      "vertical_upper_margin_m": -0.09834374045777462
    },
    {
      "actual_left_finger_qpos_m": [
        0.023583028465509415,
        0.02150672674179077
      ],
      "angular_speed_rps": 0.016029260840389265,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006818977454228492,
        0.16655817123165317,
        0.0009620826313465058
      ],
      "can_pose": [
        -0.29167500138282776,
        -0.1533137559890747,
        0.9430977702140808,
        0.005269121378660202,
        0.699306070804596,
        0.04590708389878273,
        0.7133274674415588
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0007451336865374181,
      "can_relative_translation_from_partial_start_m": [
        6.125867366790771e-05,
        -1.7404556274414062e-05,
        -0.00011840462684631348
      ],
      "can_to_box_relative_orientation_rad": 1.4993664181585902,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.008372988551855087,
        -0.008372988551855087
      ],
      "left_finger_qf_audit_only": [
        6.78726053237915,
        -6.78728723526001
      ],
      "left_finger_qvel_mps": [
        -0.0015140705509111285,
        0.001073447521775961
      ],
      "linear_speed_mps": 0.0028818436020668532,
      "local_corner_max_m": [
        0.05162814178624789,
        0.20310533904288064,
        0.0369905945205149
      ],
      "local_corner_min_m": [
        -0.052991937277093615,
        0.1300110034204257,
        -0.035066429257821885
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07680694007182443,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11283545196099282,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025254197480901977,
      "step_index": 1982,
      "timestamp_seconds": 7.928000376559794,
      "trace_row": 1982,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09833994372937928,
      "vertical_lower_margin_m": 0.10824560810692435,
      "vertical_upper_margin_m": -0.09833994372937928
    },
    {
      "actual_left_finger_qpos_m": [
        0.02358318492770195,
        0.021507376804947853
      ],
      "angular_speed_rps": 0.016289619630937006,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006767563692220979,
        0.16655526301156154,
        0.0009549708802490953
      ],
      "can_pose": [
        -0.291684627532959,
        -0.1533086597919464,
        0.9430961608886719,
        0.005240125115960836,
        0.6992973685264587,
        0.04591592773795128,
        0.7133356332778931
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0008101687205522319,
      "can_relative_translation_from_partial_start_m": [
        6.635487079620361e-05,
        -1.901388168334961e-05,
        -0.00012803077697753906
      ],
      "can_to_box_relative_orientation_rad": 1.4993967650673288,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.008210287429392338,
        -0.008210287429392338
      ],
      "left_finger_qf_audit_only": [
        6.787126541137695,
        -6.787156581878662
      ],
      "left_finger_qvel_mps": [
        -0.0015109024243429303,
        0.0010378038277849555
      ],
      "linear_speed_mps": 0.0027525432362128493,
      "local_corner_max_m": [
        0.051634030272880604,
        0.20310190647754367,
        0.03698673042615075
      ],
      "local_corner_min_m": [
        -0.0529875430113248,
        0.1300086195455794,
        -0.03507678866565256
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07681405182292184,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11284581136882349,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02525859174667079,
      "step_index": 1983,
      "timestamp_seconds": 7.932000376749784,
      "trace_row": 1983,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09833651116404231,
      "vertical_lower_margin_m": 0.10824322423207805,
      "vertical_upper_margin_m": -0.09833651116404231
    },
    {
      "actual_left_finger_qpos_m": [
        0.02358333207666874,
        0.021508174017071724
      ],
      "angular_speed_rps": 0.016339569602122406,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000671391004812949,
        0.16655188257233522,
        0.0009481782427032681
      ],
      "can_pose": [
        -0.2916940450668335,
        -0.1533033549785614,
        0.9430939555168152,
        0.005211250856518745,
        0.6992892622947693,
        0.04592651501297951,
        0.7133431434631348
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0008754947148968228,
      "can_relative_translation_from_partial_start_m": [
        7.165968418121338e-05,
        -2.1219253540039062e-05,
        -0.00013744831085205078
      ],
      "can_to_box_relative_orientation_rad": 1.4994245277223421,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.008047586306929588,
        -0.008047586306929588
      ],
      "left_finger_qf_audit_only": [
        6.786990165710449,
        -6.787021636962891
      ],
      "left_finger_qvel_mps": [
        -0.0014748547691851854,
        0.0010037940228357911
      ],
      "linear_speed_mps": 0.00275788237141812,
      "local_corner_max_m": [
        0.051640286689067116,
        0.20309805925635882,
        0.0369832418494237
      ],
      "local_corner_min_m": [
        -0.052983068698693014,
        0.13000570588831162,
        -0.03508688536401716
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07682084446046766,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1128559080671881,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025263066059302577,
      "step_index": 1984,
      "timestamp_seconds": 7.936000376939774,
      "trace_row": 1984,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09833266394285746,
      "vertical_lower_margin_m": 0.10824031057481026,
      "vertical_upper_margin_m": -0.09833266394285746
    },
    {
      "actual_left_finger_qpos_m": [
        0.023583214730024338,
        0.02150919660925865
      ],
      "angular_speed_rps": 0.01595670284057853,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000666141418753402,
        0.1665485575449147,
        0.0009413200327270665
      ],
      "can_pose": [
        -0.29170340299606323,
        -0.15329815447330475,
        0.943091869354248,
        0.0051828366704285145,
        0.6992809772491455,
        0.04593569412827492,
        0.713350772857666
      ],
      "can_relative_orientation_from_partial_start_rad": 0.000939277104119726,
      "can_relative_translation_from_partial_start_m": [
        7.686018943786621e-05,
        -2.3305416107177734e-05,
        -0.0001468062400817871
      ],
      "can_to_box_relative_orientation_rad": 1.4994535512727345,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.007884885184466839,
        -0.007884885184466839
      ],
      "left_finger_qf_audit_only": [
        6.786860942840576,
        -6.7868876457214355
      ],
      "left_finger_qvel_mps": [
        -0.0015060389414429665,
        0.0010436131851747632
      ],
      "linear_speed_mps": 0.0027268131278608584,
      "local_corner_max_m": [
        0.0516463105537768,
        0.20309422380254227,
        0.03697957461317969
      ],
      "local_corner_min_m": [
        -0.052978593391283635,
        0.13000289128728715,
        -0.035096934547725556
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07682770267044386,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11286595725089649,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025267541366711957,
      "step_index": 1985,
      "timestamp_seconds": 7.940000377129763,
      "trace_row": 1985,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09832882848904091,
      "vertical_lower_margin_m": 0.10823749597378579,
      "vertical_upper_margin_m": -0.09832882848904091
    },
    {
      "actual_left_finger_qpos_m": [
        0.02358303964138031,
        0.021510260179638863
      ],
      "angular_speed_rps": 0.016113158568034556,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000660999479321217,
        0.16654513054238085,
        0.0009347740925447767
      ],
      "can_pose": [
        -0.29171255230903625,
        -0.15329307317733765,
        0.9430896043777466,
        0.005154244601726532,
        0.6992732882499695,
        0.04594621807336807,
        0.7133579254150391
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0010037108276671816,
      "can_relative_translation_from_partial_start_m": [
        8.194148540496826e-05,
        -2.5570392608642578e-05,
        -0.00015595555305480957
      ],
      "can_to_box_relative_orientation_rad": 1.49948098455766,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.007722183596342802,
        -0.007722183596342802
      ],
      "left_finger_qf_audit_only": [
        6.786721229553223,
        -6.786745071411133
      ],
      "left_finger_qvel_mps": [
        -0.0015218453481793404,
        0.001062203897163272
      ],
      "linear_speed_mps": 0.0026769806247397736,
      "local_corner_max_m": [
        0.05165233735008426,
        0.20309030773826242,
        0.03697627627410749
      ],
      "local_corner_min_m": [
        -0.05297433630872672,
        0.12999995334649928,
        -0.035106728089017936
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07683424861062615,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11287575079218887,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02527179844926887,
      "step_index": 1986,
      "timestamp_seconds": 7.944000377319753,
      "trace_row": 1986,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09832491242476106,
      "vertical_lower_margin_m": 0.10823455803299792,
      "vertical_upper_margin_m": -0.09832491242476106
    },
    {
      "actual_left_finger_qpos_m": [
        0.023582760244607925,
        0.021511437371373177
      ],
      "angular_speed_rps": 0.015599728837728567,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000656015477331684,
        0.16654186287078854,
        0.0009282516426393217
      ],
      "can_pose": [
        -0.2917214632034302,
        -0.15328814089298248,
        0.9430874586105347,
        0.0051274485886096954,
        0.6992638111114502,
        0.04595547169446945,
        0.7133668661117554
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001065795506768637,
      "can_relative_translation_from_partial_start_m": [
        8.687376976013184e-05,
        -2.771615982055664e-05,
        -0.00016486644744873047
      ],
      "can_to_box_relative_orientation_rad": 1.4995075967297018,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.007559482008218765,
        -0.007559482008218765
      ],
      "left_finger_qf_audit_only": [
        6.786594390869141,
        -6.786620140075684
      ],
      "left_finger_qvel_mps": [
        -0.0015873988159000874,
        0.0011273842537775636
      ],
      "linear_speed_mps": 0.002602111816585006,
      "local_corner_max_m": [
        0.05165810130038054,
        0.20308675635241402,
        0.03697294799295242
      ],
      "local_corner_min_m": [
        -0.05297013225504388,
        0.12999696938916305,
        -0.03511644470767378
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07684077106053161,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11288546741084471,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025276002502951714,
      "step_index": 1987,
      "timestamp_seconds": 7.948000377509743,
      "trace_row": 1987,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09832136103891266,
      "vertical_lower_margin_m": 0.1082315740756617,
      "vertical_upper_margin_m": -0.09832136103891266
    },
    {
      "actual_left_finger_qpos_m": [
        0.023582417517900467,
        0.021512676030397415
      ],
      "angular_speed_rps": 0.015110229617688866,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006509900810128255,
        0.16653838965153,
        0.0009219669756894144
      ],
      "can_pose": [
        -0.2917300760746002,
        -0.15328314900398254,
        0.9430853128433228,
        0.005099742207676172,
        0.6992567777633667,
        0.04596270993351936,
        0.7133734822273254
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0011260978623728179,
      "can_relative_translation_from_partial_start_m": [
        9.18656587600708e-05,
        -2.9861927032470703e-05,
        -0.00017347931861877441
      ],
      "can_to_box_relative_orientation_rad": 1.4995382285855492,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0073967804200947285,
        -0.0073967804200947285
      ],
      "left_finger_qf_audit_only": [
        6.7864508628845215,
        -6.786477088928223
      ],
      "left_finger_qvel_mps": [
        -0.0016436954028904438,
        0.001186072826385498
      ],
      "linear_speed_mps": 0.002545888998166731,
      "local_corner_max_m": [
        0.051663738046440644,
        0.2030825904660607,
        0.036969578771296696
      ],
      "local_corner_min_m": [
        -0.052965718208466295,
        0.1299941888369993,
        -0.03512564481991787
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07684705572748152,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1128946675230888,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025280416549529297,
      "step_index": 1988,
      "timestamp_seconds": 7.952000377699733,
      "trace_row": 1988,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09831719515255934,
      "vertical_lower_margin_m": 0.10822879352349796,
      "vertical_upper_margin_m": -0.09831719515255934
    },
    {
      "actual_left_finger_qpos_m": [
        0.02358204498887062,
        0.021514002233743668
      ],
      "angular_speed_rps": 0.01497773328544562,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006460677974730045,
        0.16653494812862157,
        0.0009160507216555147
      ],
      "can_pose": [
        -0.2917383313179016,
        -0.15327827632427216,
        0.9430829882621765,
        0.005073435138911009,
        0.6992485523223877,
        0.045971620827913284,
        0.7133811116218567
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001185935416973821,
      "can_relative_translation_from_partial_start_m": [
        9.673833847045898e-05,
        -3.218650817871094e-05,
        -0.00018173456192016602
      ],
      "can_to_box_relative_orientation_rad": 1.4995645591049387,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.007234078831970692,
        -0.007234078831970692
      ],
      "left_finger_qf_audit_only": [
        6.78631591796875,
        -6.786348819732666
      ],
      "left_finger_qvel_mps": [
        -0.001720891217701137,
        0.001251197885721922
      ],
      "linear_speed_mps": 0.0024659647932915845,
      "local_corner_max_m": [
        0.05166941077289011,
        0.20307875498432393,
        0.03696669186181639
      ],
      "local_corner_min_m": [
        -0.05296154636783612,
        0.12999114127291922,
        -0.03513459041850536
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07685297198151542,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1129036131216763,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02528458839015947,
      "step_index": 1989,
      "timestamp_seconds": 7.956000377889723,
      "trace_row": 1989,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09831335967082257,
      "vertical_lower_margin_m": 0.10822574595941786,
      "vertical_upper_margin_m": -0.09831335967082257
    },
    {
      "actual_left_finger_qpos_m": [
        0.023581426590681076,
        0.021515486761927605
      ],
      "angular_speed_rps": 0.0148971051307161,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006412784195426735,
        0.16653119613612244,
        0.0009102029970803893
      ],
      "can_pose": [
        -0.291746586561203,
        -0.1532735526561737,
        0.9430801868438721,
        0.005047852173447609,
        0.699240505695343,
        0.04598229005932808,
        0.7133885025978088
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0012453553670097198,
      "can_relative_translation_from_partial_start_m": [
        0.00010146200656890869,
        -3.49879264831543e-05,
        -0.00018998980522155762
      ],
      "can_to_box_relative_orientation_rad": 1.499587420707758,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.007071377243846655,
        -0.007071377243846655
      ],
      "left_finger_qf_audit_only": [
        6.786180019378662,
        -6.7862114906311035
      ],
      "left_finger_qvel_mps": [
        -0.0018957627471536398,
        0.001400043722242117
      ],
      "linear_speed_mps": 0.0024787852045785696,
      "local_corner_max_m": [
        0.05167509589829483,
        0.20307474566314399,
        0.036963926290140225
      ],
      "local_corner_min_m": [
        -0.05295765273738018,
        0.1299876466091009,
        -0.03514352029597945
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07685881970609054,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11291254299915038,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025288482020615413,
      "step_index": 1990,
      "timestamp_seconds": 7.960000378079712,
      "trace_row": 1990,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09830935034964262,
      "vertical_lower_margin_m": 0.10822225129559954,
      "vertical_upper_margin_m": -0.09830935034964262
    },
    {
      "actual_left_finger_qpos_m": [
        0.02358078397810459,
        0.021517036482691765
      ],
      "angular_speed_rps": 0.014876316947143184,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006364806381236321,
        0.16652758444735327,
        0.0009045253904761963
      ],
      "can_pose": [
        -0.2917546033859253,
        -0.15326881408691406,
        0.943077564239502,
        0.005022452678531408,
        0.699231743812561,
        0.0459921695291996,
        0.7133966088294983
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0013046548552220851,
      "can_relative_translation_from_partial_start_m": [
        0.00010620057582855225,
        -3.7610530853271484e-05,
        -0.00019800662994384766
      ],
      "can_to_box_relative_orientation_rad": 1.4996111193090993,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.006908675655722618,
        -0.006908675655722618
      ],
      "left_finger_qf_audit_only": [
        6.78603458404541,
        -6.786069393157959
      ],
      "left_finger_qvel_mps": [
        -0.0017786278622224927,
        0.0013219652464613318
      ],
      "linear_speed_mps": 0.002418697506495566,
      "local_corner_max_m": [
        0.05168072415942643,
        0.20307090679291806,
        0.036961326010028106
      ],
      "local_corner_min_m": [
        -0.05295368543567369,
        0.12998426210178848,
        -0.03515227522907571
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07686449731269474,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11292129793224664,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0252924493223219,
      "step_index": 1991,
      "timestamp_seconds": 7.964000378269702,
      "trace_row": 1991,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0983055114794167,
      "vertical_lower_margin_m": 0.10821886678828713,
      "vertical_upper_margin_m": -0.0983055114794167
    },
    {
      "actual_left_finger_qpos_m": [
        0.023579971864819527,
        0.02151869237422943
      ],
      "angular_speed_rps": 0.014232375736026894,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006318726195301272,
        0.16652395170824297,
        0.0008989805732234069
      ],
      "can_pose": [
        -0.29176217317581177,
        -0.15326422452926636,
        0.9430752396583557,
        0.004997069016098976,
        0.6992232203483582,
        0.04599732533097267,
        0.7134047746658325
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001360987015674994,
      "can_relative_translation_from_partial_start_m": [
        0.00011079013347625732,
        -3.993511199951172e-05,
        -0.00020557641983032227
      ],
      "can_to_box_relative_orientation_rad": 1.499641273060494,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.006745974067598581,
        -0.006745974067598581
      ],
      "left_finger_qf_audit_only": [
        6.785890579223633,
        -6.785916328430176
      ],
      "left_finger_qvel_mps": [
        -0.0019568384159356356,
        0.001464939210563898
      ],
      "linear_speed_mps": 0.002288141001374918,
      "local_corner_max_m": [
        0.0516857703658172,
        0.20306674488017473,
        0.03695853005485572
      ],
      "local_corner_min_m": [
        -0.052949515604877484,
        0.1299811585363112,
        -0.03516056890840891
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07687004212994752,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11292959161157984,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025296619153118108,
      "step_index": 1992,
      "timestamp_seconds": 7.968000378459692,
      "trace_row": 1992,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09830134956667337,
      "vertical_lower_margin_m": 0.10821576322280985,
      "vertical_upper_margin_m": -0.09830134956667337
    },
    {
      "actual_left_finger_qpos_m": [
        0.02357911877334118,
        0.02152046374976635
      ],
      "angular_speed_rps": 0.014452197764490268,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006271122602387325,
        0.16652026796550257,
        0.0008938345315259721
      ],
      "can_pose": [
        -0.29176953434944153,
        -0.1532595157623291,
        0.9430725574493408,
        0.004972490947693586,
        0.6992142200469971,
        0.04600619897246361,
        0.7134132385253906
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0014185243237784802,
      "can_relative_translation_from_partial_start_m": [
        0.00011549890041351318,
        -4.26173210144043e-05,
        -0.000212937593460083
      ],
      "can_to_box_relative_orientation_rad": 1.499665169638177,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0065832724794745445,
        -0.0065832724794745445
      ],
      "left_finger_qf_audit_only": [
        6.785747528076172,
        -6.785783290863037
      ],
      "left_finger_qvel_mps": [
        -0.0018146410584449768,
        0.0013602904509752989
      ],
      "linear_speed_mps": 0.002285191465436807,
      "local_corner_max_m": [
        0.051691277161819316,
        0.2030628522146588,
        0.03695636357843074
      ],
      "local_corner_min_m": [
        -0.05294550168229678,
        0.12997768371634633,
        -0.035168694515378796
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07687518817164496,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11293771721854973,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02530063307569881,
      "step_index": 1993,
      "timestamp_seconds": 7.972000378649682,
      "trace_row": 1993,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09829745690115745,
      "vertical_lower_margin_m": 0.10821228840284497,
      "vertical_upper_margin_m": -0.09829745690115745
    },
    {
      "actual_left_finger_qpos_m": [
        0.02357816882431507,
        0.02152232639491558
      ],
      "angular_speed_rps": 0.014954385532609398,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006225044907614274,
        0.16651634786568192,
        0.0008887097649871167
      ],
      "can_pose": [
        -0.291777104139328,
        -0.15325498580932617,
        0.9430694580078125,
        0.00494755944237113,
        0.699205756187439,
        0.046018123626708984,
        0.7134209275245667
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0014779249406509062,
      "can_relative_translation_from_partial_start_m": [
        0.00012002885341644287,
        -4.571676254272461e-05,
        -0.00022050738334655762
      ],
      "can_to_box_relative_orientation_rad": 1.4996853754788373,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.006420570891350508,
        -0.006420570891350508
      ],
      "left_finger_qf_audit_only": [
        6.785608768463135,
        -6.785638809204102
      ],
      "left_finger_qvel_mps": [
        -0.0018115839920938015,
        0.0013201921246945858
      ],
      "linear_speed_mps": 0.002337583188577445,
      "local_corner_max_m": [
        0.05169688421869753,
        0.2030588291164651,
        0.03695439260241229
      ],
      "local_corner_min_m": [
        -0.05294189320022036,
        0.12997386661489874,
        -0.035176973072438056
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07688031293818381,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11294599577560899,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025304241557775234,
      "step_index": 1994,
      "timestamp_seconds": 7.976000378839672,
      "trace_row": 1994,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09829343380296375,
      "vertical_lower_margin_m": 0.10820847130139738,
      "vertical_upper_margin_m": -0.09829343380296375
    },
    {
      "actual_left_finger_qpos_m": [
        0.02357710525393486,
        0.021524326875805855
      ],
      "angular_speed_rps": 0.01398643733858517,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006179475531079281,
        0.16651271617531715,
        0.0008835119861361207
      ],
      "can_pose": [
        -0.2917843163013458,
        -0.15325045585632324,
        0.9430670142173767,
        0.004923122003674507,
        0.6991969347000122,
        0.04602411016821861,
        0.7134293913841248
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0015334059592296378,
      "can_relative_translation_from_partial_start_m": [
        0.00012455880641937256,
        -4.8160552978515625e-05,
        -0.00022771954536437988
      ],
      "can_to_box_relative_orientation_rad": 1.4997130272201593,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.006257869303226471,
        -0.006257869303226471
      ],
      "left_finger_qf_audit_only": [
        6.785465240478516,
        -6.785490989685059
      ],
      "left_finger_qvel_mps": [
        -0.001867431914433837,
        0.0014302844647318125
      ],
      "linear_speed_mps": 0.002215116523688523,
      "local_corner_max_m": [
        0.05170194753578042,
        0.20305480916255592,
        0.036951961834986724
      ],
      "local_corner_min_m": [
        -0.0529378426419963,
        0.1299706231880784,
        -0.03518493786271448
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07688551071703481,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11295396056588541,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02530829211599929,
      "step_index": 1995,
      "timestamp_seconds": 7.980000379029661,
      "trace_row": 1995,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09828941384905455,
      "vertical_lower_margin_m": 0.10820522787457704,
      "vertical_upper_margin_m": -0.09828941384905455
    },
    {
      "actual_left_finger_qpos_m": [
        0.023576002568006516,
        0.021526403725147247
      ],
      "angular_speed_rps": 0.013598069773168048,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006135767085734822,
        0.1665087527109358,
        0.0008786053506863456
      ],
      "can_pose": [
        -0.29179126024246216,
        -0.15324611961841583,
        0.9430641531944275,
        0.004899196792393923,
        0.6991889476776123,
        0.04603090137243271,
        0.7134369611740112
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0015876383438943726,
      "can_relative_translation_from_partial_start_m": [
        0.00012889504432678223,
        -5.1021575927734375e-05,
        -0.0002346634864807129
      ],
      "can_to_box_relative_orientation_rad": 1.4997388035450652,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.006095167715102434,
        -0.006095167715102434
      ],
      "left_finger_qf_audit_only": [
        6.785324573516846,
        -6.785356521606445
      ],
      "left_finger_qvel_mps": [
        -0.0019960603676736355,
        0.0014832421438768506
      ],
      "linear_speed_mps": 0.002168045239790581,
      "local_corner_max_m": [
        0.05170689081605592,
        0.20305045929675114,
        0.036949768975333364
      ],
      "local_corner_min_m": [
        -0.052934044233202915,
        0.12996704612512044,
        -0.03519255827396067
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07689041735248459,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1129615809771316,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025312090524792677,
      "step_index": 1996,
      "timestamp_seconds": 7.984000379219651,
      "trace_row": 1996,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09828506398324978,
      "vertical_lower_margin_m": 0.10820165081161909,
      "vertical_upper_margin_m": -0.09828506398324978
    },
    {
      "actual_left_finger_qpos_m": [
        0.023574842140078545,
        0.02152838557958603
      ],
      "angular_speed_rps": 0.014436323268935751,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006090445997636584,
        0.166504758388488,
        0.0008738250587582708
      ],
      "can_pose": [
        -0.29179832339286804,
        -0.15324166417121887,
        0.9430608749389648,
        0.004876179154962301,
        0.6991792917251587,
        0.04604242369532585,
        0.713445782661438
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0016445772321838875,
      "can_relative_translation_from_partial_start_m": [
        0.00013335049152374268,
        -5.429983139038086e-05,
        -0.00024172663688659668
      ],
      "can_to_box_relative_orientation_rad": 1.4997568091157523,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.005932466126978397,
        -0.005932466126978397
      ],
      "left_finger_qf_audit_only": [
        6.785168647766113,
        -6.785201549530029
      ],
      "left_finger_qvel_mps": [
        -0.0020541069097816944,
        0.0015598477330058813
      ],
      "linear_speed_mps": 0.0022428505107012467,
      "local_corner_max_m": [
        0.05171238871951114,
        0.20304657018702088,
        0.036948086587592244
      ],
      "local_corner_min_m": [
        -0.05293047791903849,
        0.1299629465899551,
        -0.0352004364700757
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07689519764441266,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11296945917324663,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025315656838957104,
      "step_index": 1997,
      "timestamp_seconds": 7.988000379409641,
      "trace_row": 1997,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09828117487351952,
      "vertical_lower_margin_m": 0.10819755127645375,
      "vertical_upper_margin_m": -0.09828117487351952
    },
    {
      "actual_left_finger_qpos_m": [
        0.02357352152466774,
        0.02153066359460354
      ],
      "angular_speed_rps": 0.013204901592171622,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006048022724705615,
        0.16650072523854786,
        0.0008692691244798212
      ],
      "can_pose": [
        -0.2918047606945038,
        -0.153237447142601,
        0.9430579543113708,
        0.004853307269513607,
        0.6991706490516663,
        0.04604799300432205,
        0.7134540677070618
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001696908952115783,
      "can_relative_translation_from_partial_start_m": [
        0.00013756752014160156,
        -5.7220458984375e-05,
        -0.00024816393852233887
      ],
      "can_to_box_relative_orientation_rad": 1.4997827495359908,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.005769764538854361,
        -0.005769764538854361
      ],
      "left_finger_qf_audit_only": [
        6.785018444061279,
        -6.785052299499512
      ],
      "left_finger_qvel_mps": [
        -0.0020963288843631744,
        0.0016099396161735058
      ],
      "linear_speed_mps": 0.00205779374908013,
      "local_corner_max_m": [
        0.05171710194640716,
        0.20304220705009246,
        0.036946149797654204
      ],
      "local_corner_min_m": [
        -0.052926706491348285,
        0.12995924342700327,
        -0.03520761154869456
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07689975357869111,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1129766342518655,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025319428266647306,
      "step_index": 1998,
      "timestamp_seconds": 7.992000379599631,
      "trace_row": 1998,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0982768117365911,
      "vertical_lower_margin_m": 0.10819384811350191,
      "vertical_upper_margin_m": -0.0982768117365911
    },
    {
      "actual_left_finger_qpos_m": [
        0.023572124540805817,
        0.021532896906137466
      ],
      "angular_speed_rps": 0.013162834519684568,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006004097133584518,
        0.16649664352988092,
        0.000864978252678672
      ],
      "can_pose": [
        -0.2918110489845276,
        -0.1532330960035324,
        0.9430548548698425,
        0.004830566234886646,
        0.6991626024246216,
        0.0460553914308548,
        0.7134615778923035
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001749440903120253,
      "can_relative_translation_from_partial_start_m": [
        0.00014191865921020508,
        -6.031990051269531e-05,
        -0.0002544522285461426
      ],
      "can_to_box_relative_orientation_rad": 1.4998059677721207,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.005607062950730324,
        -0.005607062950730324
      ],
      "left_finger_qf_audit_only": [
        6.784862995147705,
        -6.7848968505859375
      ],
      "left_finger_qvel_mps": [
        -0.0020790831185877323,
        0.0015957080759108067
      ],
      "linear_speed_mps": 0.002062788372838372,
      "local_corner_max_m": [
        0.05172211681453298,
        0.20303785352563453,
        0.03694453488450439
      ],
      "local_corner_min_m": [
        -0.052922936241249885,
        0.1299554335341273,
        -0.035214578379147043
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07690404445049226,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11298360108231797,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025323198516745707,
      "step_index": 1999,
      "timestamp_seconds": 7.996000379789621,
      "trace_row": 1999,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09827245821213317,
      "vertical_lower_margin_m": 0.10819003822062595,
      "vertical_upper_margin_m": -0.09827245821213317
    },
    {
      "actual_left_finger_qpos_m": [
        0.0235707126557827,
        0.021535266190767288
      ],
      "angular_speed_rps": 0.013634007700449235,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005961538111855236,
        0.1664924387034198,
        0.0008605980739094798
      ],
      "can_pose": [
        -0.2918176054954529,
        -0.15322890877723694,
        0.9430513978004456,
        0.004808185622096062,
        0.6991541385650635,
        0.046065881848335266,
        0.713469386100769
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001803570599549843,
      "can_relative_translation_from_partial_start_m": [
        0.00014610588550567627,
        -6.377696990966797e-05,
        -0.00026100873947143555
      ],
      "can_to_box_relative_orientation_rad": 1.499824436519055,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.005444361362606287,
        -0.005444361362606287
      ],
      "left_finger_qf_audit_only": [
        6.7847161293029785,
        -6.784752368927002
      ],
      "left_finger_qvel_mps": [
        -0.0022421281319111586,
        0.001742771826684475
      ],
      "linear_speed_mps": 0.002128262517494957,
      "local_corner_max_m": [
        0.051727251354541315,
        0.20303362654721158,
        0.03694304602019016
      ],
      "local_corner_min_m": [
        -0.05291955897691236,
        0.129951250859628,
        -0.0352218498723712
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07690842462926145,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11299087257554213,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02532657578108323,
      "step_index": 2000,
      "timestamp_seconds": 8.00000037997961,
      "trace_row": 2000,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09826823123371022,
      "vertical_lower_margin_m": 0.10818585554612664,
      "vertical_upper_margin_m": -0.09826823123371022
    },
    {
      "actual_left_finger_qpos_m": [
        0.023569153621792793,
        0.02153770998120308
      ],
      "angular_speed_rps": 0.013232733818974293,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005920927677552923,
        0.16648855030211973,
        0.0008565176598449575
      ],
      "can_pose": [
        -0.2918235957622528,
        -0.1532248854637146,
        0.9430484771728516,
        0.004786123521625996,
        0.6991447806358337,
        0.04607275500893593,
        0.7134782671928406
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001855973815498014,
      "can_relative_translation_from_partial_start_m": [
        0.00015012919902801514,
        -6.669759750366211e-05,
        -0.0002669990062713623
      ],
      "can_to_box_relative_orientation_rad": 1.4998474310284544,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.00528165977448225,
        -0.00528165977448225
      ],
      "left_finger_qf_audit_only": [
        6.784562110900879,
        -6.78460168838501
      ],
      "left_finger_qvel_mps": [
        -0.0021568776573985815,
        0.0016481314087286592
      ],
      "linear_speed_mps": 0.0019461565940882297,
      "local_corner_max_m": [
        0.05173189130147485,
        0.20302960370868905,
        0.03694167466859666
      ],
      "local_corner_min_m": [
        -0.052916076836985404,
        0.1299474968955504,
        -0.03522863934890674
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07691250504332597,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11299766205207767,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025330057921010188,
      "step_index": 2001,
      "timestamp_seconds": 8.0040003801696,
      "trace_row": 2001,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0982642083951877,
      "vertical_lower_margin_m": 0.10818210158204905,
      "vertical_upper_margin_m": -0.0982642083951877
    },
    {
      "actual_left_finger_qpos_m": [
        0.023567501455545425,
        0.021540308371186256
      ],
      "angular_speed_rps": 0.012612291846741522,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005877730220168187,
        0.1664842785885461,
        0.0008527473942737673
      ],
      "can_pose": [
        -0.2918291389942169,
        -0.15322059392929077,
        0.9430451989173889,
        0.004764921963214874,
        0.6991358399391174,
        0.04607842490077019,
        0.713486909866333
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0019058253711544473,
      "can_relative_translation_from_partial_start_m": [
        0.00015442073345184326,
        -6.99758529663086e-05,
        -0.00027254223823547363
      ],
      "can_to_box_relative_orientation_rad": 1.4998708180749498,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.005118958186358213,
        -0.005118958186358213
      ],
      "left_finger_qf_audit_only": [
        6.784405708312988,
        -6.784439563751221
      ],
      "left_finger_qvel_mps": [
        -0.002063857391476631,
        0.0015640276251360774
      ],
      "linear_speed_mps": 0.0019347422552470983,
      "local_corner_max_m": [
        0.051736689360842913,
        0.20302514684476647,
        0.03694044657855461
      ],
      "local_corner_min_m": [
        -0.05291223540487655,
        0.1299434103323257,
        -0.035234951790007074
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07691627530889716,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.113003974493178,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02533389935311904,
      "step_index": 2002,
      "timestamp_seconds": 8.00800038035959,
      "trace_row": 2002,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09825975153126511,
      "vertical_lower_margin_m": 0.10817801501882435,
      "vertical_upper_margin_m": -0.09825975153126511
    },
    {
      "actual_left_finger_qpos_m": [
        0.023565782234072685,
        0.02154289372265339
      ],
      "angular_speed_rps": 0.012853406660371406,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005838096041107521,
        0.16648006138899618,
        0.0008488083790790801
      ],
      "can_pose": [
        -0.29183509945869446,
        -0.15321668982505798,
        0.9430417418479919,
        0.004743634257465601,
        0.699127733707428,
        0.04608767479658127,
        0.7134944200515747
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0019569806537071688,
      "can_relative_translation_from_partial_start_m": [
        0.00015832483768463135,
        -7.343292236328125e-05,
        -0.0002785027027130127
      ],
      "can_to_box_relative_orientation_rad": 1.4998893885342817,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.004956256598234177,
        -0.004956256598234177
      ],
      "left_finger_qf_audit_only": [
        6.7842631340026855,
        -6.784292221069336
      ],
      "left_finger_qvel_mps": [
        -0.002377360360696912,
        0.0018630118574947119
      ],
      "linear_speed_mps": 0.001979906713487987,
      "local_corner_max_m": [
        0.05174142770220677,
        0.20302086985752033,
        0.036939214106723406
      ],
      "local_corner_min_m": [
        -0.05290904691042825,
        0.12993925292047204,
        -0.035241597348565246
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07692021432409185,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11301062005173618,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025337087847567344,
      "step_index": 2003,
      "timestamp_seconds": 8.01200038054958,
      "trace_row": 2003,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09825547454401896,
      "vertical_lower_margin_m": 0.10817385760697068,
      "vertical_upper_margin_m": -0.09825547454401896
    },
    {
      "actual_left_finger_qpos_m": [
        0.023605259135365486,
        0.021506238728761673
      ],
      "angular_speed_rps": 0.15569754940163763,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005630133606852328,
        0.16639722630140552,
        0.0008226977908598609
      ],
      "can_pose": [
        -0.2918592691421509,
        -0.153196781873703,
        0.9429451823234558,
        0.004871537443250418,
        0.6993172764778137,
        0.04617520794272423,
        0.7133020162582397
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001662645601421287,
      "can_relative_translation_from_partial_start_m": [
        0.00017823278903961182,
        -0.00016999244689941406,
        -0.0003026723861694336
      ],
      "can_to_box_relative_orientation_rad": 1.499577323673631,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.00479355501011014,
        -0.00479355501011014
      ],
      "left_finger_qf_audit_only": [
        6.784097194671631,
        -6.784139156341553
      ],
      "left_finger_qvel_mps": [
        -0.008938267827033997,
        0.009853247553110123
      ],
      "linear_speed_mps": 0.025377451760038753,
      "local_corner_max_m": [
        0.051769356330727934,
        0.20293373612948495,
        0.03689426265415502
      ],
      "local_corner_min_m": [
        -0.0528953830520984,
        0.1298607164733261,
        -0.0352488670724353
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07694632491231107,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11301788977560623,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025350751705897193,
      "step_index": 2004,
      "timestamp_seconds": 8.01600038073957,
      "trace_row": 2004,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09816834081598359,
      "vertical_lower_margin_m": 0.10809532115982473,
      "vertical_upper_margin_m": -0.09816834081598359
    },
    {
      "actual_left_finger_qpos_m": [
        0.02357531525194645,
        0.021536676213145256
      ],
      "angular_speed_rps": 0.09061847765521876,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005529946638170857,
        0.16636696424774533,
        0.0008142576427559445
      ],
      "can_pose": [
        -0.29188472032546997,
        -0.1531878262758255,
        0.9429135918617249,
        0.004754878114908934,
        0.699334442615509,
        0.04631058871746063,
        0.7132772207260132
      ],
      "can_relative_orientation_from_partial_start_rad": 0.001993108690172054,
      "can_relative_translation_from_partial_start_m": [
        0.00018718838691711426,
        -0.0002015829086303711,
        -0.0003281235694885254
      ],
      "can_to_box_relative_orientation_rad": 1.4995610842768596,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.004630853421986103,
        -0.004630853421986103
      ],
      "left_finger_qf_audit_only": [
        6.787961006164551,
        -6.788158893585205
      ],
      "left_finger_qvel_mps": [
        -0.004701504483819008,
        0.0034162006340920925
      ],
      "linear_speed_mps": 0.010386056079266664,
      "local_corner_max_m": [
        0.051790613246225,
        0.202902410483496,
        0.03690095735319909
      ],
      "local_corner_min_m": [
        -0.0528966025738592,
        0.12983151801199466,
        -0.035272442067687204
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07695476506041499,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11304146477085814,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025349532184136395,
      "step_index": 2005,
      "timestamp_seconds": 8.02000038092956,
      "trace_row": 2005,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09813701516999464,
      "vertical_lower_margin_m": 0.1080661226984933,
      "vertical_upper_margin_m": -0.09813701516999464
    },
    {
      "actual_left_finger_qpos_m": [
        0.02356039360165596,
        0.021550491452217102
      ],
      "angular_speed_rps": 0.046852877271973604,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005442268542151241,
        0.16635294013181445,
        0.0008034238325796417
      ],
      "can_pose": [
        -0.2918974757194519,
        -0.1531786024570465,
        0.9429073333740234,
        0.004685219377279282,
        0.6993675827980042,
        0.04626604542136192,
        0.7132481336593628
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0020674752019311706,
      "can_relative_translation_from_partial_start_m": [
        0.00019641220569610596,
        -0.0002078413963317871,
        -0.000340878963470459
      ],
      "can_to_box_relative_orientation_rad": 1.4997227939261513,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.004468151833862066,
        -0.004468151833862066
      ],
      "left_finger_qf_audit_only": [
        6.78834867477417,
        -6.788364410400391
      ],
      "left_finger_qvel_mps": [
        -0.0018475113902240992,
        0.0016338923014700413
      ],
      "linear_speed_mps": 0.004234881562336248,
      "local_corner_max_m": [
        0.05179568025153136,
        0.2028781798463044,
        0.03688909132154827
      ],
      "local_corner_min_m": [
        -0.05288413395996161,
        0.1298277004173245,
        -0.03528224365638899
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07696559887059129,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11305126635955992,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025362000798033982,
      "step_index": 2006,
      "timestamp_seconds": 8.02400038111955,
      "trace_row": 2006,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09811278453280305,
      "vertical_lower_margin_m": 0.10806230510382314,
      "vertical_upper_margin_m": -0.09811278453280305
    },
    {
      "actual_left_finger_qpos_m": [
        0.023553453385829926,
        0.02155928686261177
      ],
      "angular_speed_rps": 0.042171299694272545,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005352121776526497,
        0.16634556650452925,
        0.0007888018515854189
      ],
      "can_pose": [
        -0.2919180691242218,
        -0.1531696915626526,
        0.9429032206535339,
        0.004618506412953138,
        0.699401319026947,
        0.046285297721624374,
        0.7132141590118408
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0022044656537187988,
      "can_relative_translation_from_partial_start_m": [
        0.00020532310009002686,
        -0.00021195411682128906,
        -0.00036147236824035645
      ],
      "can_to_box_relative_orientation_rad": 1.4997926585224584,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0043054502457380295,
        -0.0043054502457380295
      ],
      "left_finger_qf_audit_only": [
        6.789031028747559,
        -6.789046287536621
      ],
      "left_finger_qvel_mps": [
        -0.0005435764905996621,
        0.0003845435567200184
      ],
      "linear_speed_mps": 0.005703106496162985,
      "local_corner_max_m": [
        0.051806283368709904,
        0.20286450813764945,
        0.03687732410258204
      ],
      "local_corner_min_m": [
        -0.052876707724015204,
        0.12982662487140906,
        -0.035299720399411205
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07698022085158551,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11306874310258214,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025369427033980388,
      "step_index": 2007,
      "timestamp_seconds": 8.028000381309539,
      "trace_row": 2007,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09809911282414809,
      "vertical_lower_margin_m": 0.1080612295579077,
      "vertical_upper_margin_m": -0.09809911282414809
    },
    {
      "actual_left_finger_qpos_m": [
        0.023548755794763565,
        0.021564636379480362
      ],
      "angular_speed_rps": 0.05563048294853103,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005265698088646464,
        0.16634074094183493,
        0.0007731893790976496
      ],
      "can_pose": [
        -0.2919432520866394,
        -0.1531616449356079,
        0.9428977370262146,
        0.004553739447146654,
        0.699434757232666,
        0.046360623091459274,
        0.7131768465042114
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0023935829619485915,
      "can_relative_translation_from_partial_start_m": [
        0.0002133697271347046,
        -0.000217437744140625,
        -0.000386655330657959
      ],
      "can_to_box_relative_orientation_rad": 1.499782783699499,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.004142748657613993,
        -0.004142748657613993
      ],
      "left_finger_qf_audit_only": [
        6.789769649505615,
        -6.789778709411621
      ],
      "left_finger_qvel_mps": [
        -0.0002859941450878978,
        1.9802653696388006e-05
      ],
      "linear_speed_mps": 0.0067499995474472625,
      "local_corner_max_m": [
        0.051821162781615054,
        0.20285686154681637,
        0.03686810065195578
      ],
      "local_corner_min_m": [
        -0.05287430239934432,
        0.1298246203368535,
        -0.03532172189376048
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07699583332407328,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11309074459693141,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025371832358651272,
      "step_index": 2008,
      "timestamp_seconds": 8.032000381499529,
      "trace_row": 2008,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09809146623331501,
      "vertical_lower_margin_m": 0.10805922502335213,
      "vertical_upper_margin_m": -0.09809146623331501
    },
    {
      "actual_left_finger_qpos_m": [
        0.023545503616333008,
        0.02156878635287285
      ],
      "angular_speed_rps": 0.04046266189463319,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005180657184431503,
        0.16633596574952503,
        0.0007560446712532864
      ],
      "can_pose": [
        -0.2919646203517914,
        -0.15315303206443787,
        0.9428977966308594,
        0.004488550592213869,
        0.6994691491127014,
        0.04635513946413994,
        0.7131438851356506
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0025117627929857824,
      "can_relative_translation_from_partial_start_m": [
        0.00022198259830474854,
        -0.0002173781394958496,
        -0.0004080235958099365
      ],
      "can_to_box_relative_orientation_rad": 1.4998843739294216,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.003980047069489956,
        -0.003980047069489956
      ],
      "left_finger_qf_audit_only": [
        6.790521144866943,
        -6.790531158447266
      ],
      "left_finger_qvel_mps": [
        -6.18196208961308e-05,
        -6.243819370865822e-06
      ],
      "linear_speed_mps": 0.005759708150638653,
      "local_corner_max_m": [
        0.051829202865890905,
        0.2028443595691336,
        0.03685204777494605
      ],
      "local_corner_min_m": [
        -0.05286533430277718,
        0.12982757192991645,
        -0.03533995843243948
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07701297803191764,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11310898113561041,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025380800455218414,
      "step_index": 2009,
      "timestamp_seconds": 8.036000381689519,
      "trace_row": 2009,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09807896425563224,
      "vertical_lower_margin_m": 0.1080621766164151,
      "vertical_upper_margin_m": -0.09807896425563224
    },
    {
      "actual_left_finger_qpos_m": [
        0.02354264445602894,
        0.021572666242718697
      ],
      "angular_speed_rps": 0.041065032934172976,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005096822772528709,
        0.16633190405770537,
        0.0007391924319217757
      ],
      "can_pose": [
        -0.29198718070983887,
        -0.1531447470188141,
        0.9428969025611877,
        0.0044245230965316296,
        0.6995031237602234,
        0.046373169869184494,
        0.7131097316741943
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0026529157774601627,
      "can_relative_translation_from_partial_start_m": [
        0.00023026764392852783,
        -0.00021827220916748047,
        -0.0004305839538574219
      ],
      "can_to_box_relative_orientation_rad": 1.4999520327929499,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0038173457141965628,
        -0.0038173457141965628
      ],
      "left_finger_qf_audit_only": [
        6.791255474090576,
        -6.791266918182373
      ],
      "left_finger_qvel_mps": [
        -9.162019705399871e-05,
        -1.3313721865415573e-05
      ],
      "linear_speed_mps": 0.006012544396148303,
      "local_corner_max_m": [
        0.051839071719787744,
        0.20283407475141324,
        0.036837767225754214
      ],
      "local_corner_min_m": [
        -0.052858436274293485,
        0.1298297333639975,
        -0.03535938236191066
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07702983027124916,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1131284050650816,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025387698483702106,
      "step_index": 2010,
      "timestamp_seconds": 8.040000381879508,
      "trace_row": 2010,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09806867943791188,
      "vertical_lower_margin_m": 0.10806433805049614,
      "vertical_upper_margin_m": -0.09806867943791188
    },
    {
      "actual_left_finger_qpos_m": [
        0.023539839312434196,
        0.02157634124159813
      ],
      "angular_speed_rps": 0.04775756297803919,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005013905609652647,
        0.16632817090241958,
        0.0007229006133400162
      ],
      "can_pose": [
        -0.29201143980026245,
        -0.15313686430454254,
        0.9428938627243042,
        0.004361774772405624,
        0.6995360851287842,
        0.04642651602625847,
        0.7130743265151978
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0028253803516109736,
      "can_relative_translation_from_partial_start_m": [
        0.00023815035820007324,
        -0.0002213120460510254,
        -0.00045484304428100586
      ],
      "can_to_box_relative_orientation_rad": 1.4999694323640622,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0036546443589031696,
        -0.0036546443589031696
      ],
      "left_finger_qf_audit_only": [
        6.791991710662842,
        -6.791996955871582
      ],
      "left_finger_qvel_mps": [
        -0.00013349766959436238,
        -6.275309715420008e-06
      ],
      "linear_speed_mps": 0.006422038218410775,
      "local_corner_max_m": [
        0.051851776339092714,
        0.20282639029484661,
        0.03682634022924974
      ],
      "local_corner_min_m": [
        -0.052854557461023244,
        0.12982995150999255,
        -0.03538053900256971
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07704612208983092,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11314956170574064,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025391577296972348,
      "step_index": 2011,
      "timestamp_seconds": 8.044000382069498,
      "trace_row": 2011,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09806099498134525,
      "vertical_lower_margin_m": 0.10806455619649119,
      "vertical_upper_margin_m": -0.09806099498134525
    },
    {
      "actual_left_finger_qpos_m": [
        0.023537177592515945,
        0.021579908207058907
      ],
      "angular_speed_rps": 0.03875409928203823,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0004932432607962223,
        0.16632392952029773,
        0.0007065609317351007
      ],
      "can_pose": [
        -0.2920328378677368,
        -0.1531287580728531,
        0.9428930878639221,
        0.00430032704025507,
        0.6995686888694763,
        0.046437524259090424,
        0.7130419611930847
      ],
      "can_relative_orientation_from_partial_start_rad": 0.002959047903026698,
      "can_relative_translation_from_partial_start_m": [
        0.00024625658988952637,
        -0.00022208690643310547,
        -0.0004762411117553711
      ],
      "can_to_box_relative_orientation_rad": 1.500043025363756,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0034919430036097765,
        -0.0034919430036097765
      ],
      "left_finger_qf_audit_only": [
        6.79270601272583,
        -6.792714595794678
      ],
      "left_finger_qvel_mps": [
        -0.00016097200568765402,
        -2.3396569304168224e-06
      ],
      "linear_speed_mps": 0.00572379159002715,
      "local_corner_max_m": [
        0.051860826577594166,
        0.20281580210855488,
        0.03681205769220264
      ],
      "local_corner_min_m": [
        -0.05284731309918661,
        0.12983205693204058,
        -0.035398935828732436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07706246177143583,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11316795853190337,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02539882165880898,
      "step_index": 2012,
      "timestamp_seconds": 8.048000382259488,
      "trace_row": 2012,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09805040679505352,
      "vertical_lower_margin_m": 0.10806666161853923,
      "vertical_upper_margin_m": -0.09805040679505352
    },
    {
      "actual_left_finger_qpos_m": [
        0.023534586653113365,
        0.021583344787359238
      ],
      "angular_speed_rps": 0.038271169276696416,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00048513161870131216,
        0.16632008498779494,
        0.0006905164033190192
      ],
      "can_pose": [
        -0.2920541763305664,
        -0.1531207263469696,
        0.9428923726081848,
        0.0042395032942295074,
        0.6995996832847595,
        0.046452827751636505,
        0.7130109071731567
      ],
      "can_relative_orientation_from_partial_start_rad": 0.003096419982765962,
      "can_relative_translation_from_partial_start_m": [
        0.00025428831577301025,
        -0.00022280216217041016,
        -0.0004975795745849609
      ],
      "can_to_box_relative_orientation_rad": 1.500109873340849,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0033292416483163834,
        -0.0033292416483163834
      ],
      "left_finger_qf_audit_only": [
        6.793403625488281,
        -6.7934088706970215
      ],
      "left_finger_qvel_mps": [
        -0.00016703765140846372,
        5.457899533212185e-06
      ],
      "linear_speed_mps": 0.005702796232640759,
      "local_corner_max_m": [
        0.05187019761273157,
        0.20280605600952084,
        0.03679844275532529
      ],
      "local_corner_min_m": [
        -0.05284046085013422,
        0.12983411396606903,
        -0.03541740994868725
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07707850629985191,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11318643265185818,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025405673907861373,
      "step_index": 2013,
      "timestamp_seconds": 8.052000382449478,
      "trace_row": 2013,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09804066069601948,
      "vertical_lower_margin_m": 0.10806871865256767,
      "vertical_upper_margin_m": -0.09804066069601948
    },
    {
      "actual_left_finger_qpos_m": [
        0.02353193797171116,
        0.021586880087852478
      ],
      "angular_speed_rps": 0.041859398196883654,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00047720844085380465,
        0.1663162316107537,
        0.0006750454785496296
      ],
      "can_pose": [
        -0.2920764684677124,
        -0.15311309695243835,
        0.942889928817749,
        0.0041798693127930164,
        0.6996296048164368,
        0.04649236425757408,
        0.7129793763160706
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0032534888355773444,
      "can_relative_translation_from_partial_start_m": [
        0.00026191771030426025,
        -0.00022524595260620117,
        -0.000519871711730957
      ],
      "can_to_box_relative_orientation_rad": 1.5001417988903754,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0031665402930229902,
        -0.0031665402930229902
      ],
      "left_finger_qf_audit_only": [
        6.794091701507568,
        -6.7940993309021
      ],
      "left_finger_qvel_mps": [
        -0.00020911736646667123,
        5.526293534785509e-06
      ],
      "linear_speed_mps": 0.005921988147151124,
      "local_corner_max_m": [
        0.05188138867851427,
        0.2027979156639036,
        0.03678698625410243
      ],
      "local_corner_min_m": [
        -0.05283580556022188,
        0.12983454755760382,
        -0.03543689529700317
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0770939772246213,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1132059180001741,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02541032919777371,
      "step_index": 2014,
      "timestamp_seconds": 8.056000382639468,
      "trace_row": 2014,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09803252035040223,
      "vertical_lower_margin_m": 0.10806915224410246,
      "vertical_upper_margin_m": -0.09803252035040223
    },
    {
      "actual_left_finger_qpos_m": [
        0.023529328405857086,
        0.0215904600918293
      ],
      "angular_speed_rps": 0.03757720488811688,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00046943579218367004,
        0.16631204447615877,
        0.0006595329708670161
      ],
      "can_pose": [
        -0.2920973598957062,
        -0.15310543775558472,
        0.9428884983062744,
        0.004121115896850824,
        0.6996598243713379,
        0.04651111736893654,
        0.7129488587379456
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0033919409315839324,
      "can_relative_translation_from_partial_start_m": [
        0.00026957690715789795,
        -0.00022667646408081055,
        -0.0005407631397247314
      ],
      "can_to_box_relative_orientation_rad": 1.5002009415750845,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.003003838937729597,
        -0.003003838937729597
      ],
      "left_finger_qf_audit_only": [
        6.794747352600098,
        -6.7947564125061035
      ],
      "left_finger_qvel_mps": [
        -0.00023978669196367264,
        1.737428829073906e-05
      ],
      "linear_speed_mps": 0.00557427896633853,
      "local_corner_max_m": [
        0.051890706083637994,
        0.20278823616110675,
        0.03677405287731794
      ],
      "local_corner_min_m": [
        -0.052829577668005334,
        0.1298358527912108,
        -0.03545498693558391
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07710948973230392,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11322400963875484,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025416557089990258,
      "step_index": 2015,
      "timestamp_seconds": 8.060000382829458,
      "trace_row": 2015,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09802284084760539,
      "vertical_lower_margin_m": 0.10807045747770944,
      "vertical_upper_margin_m": -0.09802284084760539
    },
    {
      "actual_left_finger_qpos_m": [
        0.023526756092905998,
        0.021593892946839333
      ],
      "angular_speed_rps": 0.03705208596237815,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0004616332665420275,
        0.16630798685168457,
        0.0006444583826948347
      ],
      "can_pose": [
        -0.292117714881897,
        -0.1530977487564087,
        0.9428871273994446,
        0.004063617438077927,
        0.699690043926239,
        0.046529676765203476,
        0.7129184007644653
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0035289872603468113,
      "can_relative_translation_from_partial_start_m": [
        0.00027726590633392334,
        -0.00022804737091064453,
        -0.0005611181259155273
      ],
      "can_to_box_relative_orientation_rad": 1.5002585331928118,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.002841137582436204,
        -0.002841137582436204
      ],
      "left_finger_qf_audit_only": [
        6.795398712158203,
        -6.795406818389893
      ],
      "left_finger_qvel_mps": [
        -0.0002676806761883199,
        2.0842242520302534e-05
      ],
      "linear_speed_mps": 0.005450490296403357,
      "local_corner_max_m": [
        0.05190003676030566,
        0.202778757104084,
        0.03676146234140676
      ],
      "local_corner_min_m": [
        -0.05282330329338969,
        0.12983721659928515,
        -0.03547254557601709
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0771245643204761,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11324156827918802,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025422831464605902,
      "step_index": 2016,
      "timestamp_seconds": 8.064000383019447,
      "trace_row": 2016,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09801336179058263,
      "vertical_lower_margin_m": 0.1080718212857838,
      "vertical_upper_margin_m": -0.09801336179058263
    },
    {
      "actual_left_finger_qpos_m": [
        0.023524083197116852,
        0.021597368642687798
      ],
      "angular_speed_rps": 0.038136079495080084,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0004539636029270988,
        0.16630390386818283,
        0.0006297170325746948
      ],
      "can_pose": [
        -0.2921384572982788,
        -0.15309029817581177,
        0.9428848624229431,
        0.0040070307441055775,
        0.6997185349464417,
        0.04656010866165161,
        0.712888777256012
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0036742185419469256,
      "can_relative_translation_from_partial_start_m": [
        0.00028471648693084717,
        -0.00023031234741210938,
        -0.0005818605422973633
      ],
      "can_to_box_relative_orientation_rad": 1.5002985691495714,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.002678436227142811,
        -0.002678436227142811
      ],
      "left_finger_qf_audit_only": [
        6.796037197113037,
        -6.796043872833252
      ],
      "left_finger_qvel_mps": [
        -0.0002998782729264349,
        2.181262243539095e-05
      ],
      "linear_speed_mps": 0.005539004087542171,
      "local_corner_max_m": [
        0.05191021910565208,
        0.20277017223310823,
        0.036750056280154486
      ],
      "local_corner_min_m": [
        -0.052818146311506275,
        0.12983763550325744,
        -0.035490622215005097
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07713930567059624,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11325964491817603,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025427988446489316,
      "step_index": 2017,
      "timestamp_seconds": 8.068000383209437,
      "trace_row": 2017,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09800477691960686,
      "vertical_lower_margin_m": 0.10807224018975609,
      "vertical_upper_margin_m": -0.09800477691960686
    },
    {
      "actual_left_finger_qpos_m": [
        0.023521503433585167,
        0.021600937470793724
      ],
      "angular_speed_rps": 0.035999609844809495,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000446446748080781,
        0.1662995944267338,
        0.0006149996152973736
      ],
      "can_pose": [
        -0.2921585440635681,
        -0.1530829221010208,
        0.9428829550743103,
        0.003950813785195351,
        0.6997461915016174,
        0.046581488102674484,
        0.7128604650497437
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0038110088205922307,
      "can_relative_translation_from_partial_start_m": [
        0.00029209256172180176,
        -0.00023221969604492188,
        -0.0006019473075866699
      ],
      "can_to_box_relative_orientation_rad": 1.5003505040340814,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0025157348718494177,
        -0.0025157348718494177
      ],
      "left_finger_qf_audit_only": [
        6.796651840209961,
        -6.796661376953125
      ],
      "left_finger_qvel_mps": [
        -0.00028981006471440196,
        3.1187955755740404e-05
      ],
      "linear_speed_mps": 0.005370768997977911,
      "local_corner_max_m": [
        0.0519194987099911,
        0.20276092168134374,
        0.03673812784319014
      ],
      "local_corner_min_m": [
        -0.052812392206152636,
        0.12983826717212388,
        -0.03550812861259539
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07715402308787356,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11327715131576632,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025433742551842956,
      "step_index": 2018,
      "timestamp_seconds": 8.072000383399427,
      "trace_row": 2018,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09799552636784238,
      "vertical_lower_margin_m": 0.10807287185862252,
      "vertical_upper_margin_m": -0.09799552636784238
    },
    {
      "actual_left_finger_qpos_m": [
        0.023518895730376244,
        0.021604418754577637
      ],
      "angular_speed_rps": 0.03539334324537464,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00043903879514078925,
        0.16629575610122338,
        0.0006006157049758265
      ],
      "can_pose": [
        -0.292178213596344,
        -0.15307565033435822,
        0.9428815245628357,
        0.0038951351307332516,
        0.6997731328010559,
        0.046602219343185425,
        0.7128329873085022
      ],
      "can_relative_orientation_from_partial_start_rad": 0.003946219303801089,
      "can_relative_translation_from_partial_start_m": [
        0.0002993643283843994,
        -0.00023365020751953125,
        -0.0006216168403625488
      ],
      "can_to_box_relative_orientation_rad": 1.500402577018574,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0023530335165560246,
        -0.0023530335165560246
      ],
      "left_finger_qf_audit_only": [
        6.797256946563721,
        -6.797266960144043
      ],
      "left_finger_qvel_mps": [
        -0.00034343849983997643,
        3.35577642545104e-05
      ],
      "linear_speed_mps": 0.0052548515150609605,
      "local_corner_max_m": [
        0.05192861543121696,
        0.20275220906263325,
        0.03672651823336165
      ],
      "local_corner_min_m": [
        -0.05280669302149854,
        0.1298393031398135,
        -0.035525286823409996
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0771684069981951,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11329430952658093,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02543944173649705,
      "step_index": 2019,
      "timestamp_seconds": 8.076000383589417,
      "trace_row": 2019,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09798681374913189,
      "vertical_lower_margin_m": 0.10807390782631215,
      "vertical_upper_margin_m": -0.09798681374913189
    },
    {
      "actual_left_finger_qpos_m": [
        0.023516274988651276,
        0.02160797454416752
      ],
      "angular_speed_rps": 0.034893789070671394,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0004317019179807813,
        0.1662914773076164,
        0.0005865062340921767
      ],
      "can_pose": [
        -0.29219764471054077,
        -0.15306846797466278,
        0.9428794384002686,
        0.0038407237734645605,
        0.6997991800308228,
        0.046624843031167984,
        0.7128061652183533
      ],
      "can_relative_orientation_from_partial_start_rad": 0.004080569829648367,
      "can_relative_translation_from_partial_start_m": [
        0.000306546688079834,
        -0.00023573637008666992,
        -0.0006410479545593262
      ],
      "can_to_box_relative_orientation_rad": 1.5004502346512745,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0021903321612626314,
        -0.0021903321612626314
      ],
      "left_finger_qf_audit_only": [
        6.797850131988525,
        -6.797860145568848
      ],
      "left_finger_qvel_mps": [
        -0.0003289263986516744,
        3.42406565323472e-05
      ],
      "linear_speed_mps": 0.005205204863874384,
      "local_corner_max_m": [
        0.05193781811959497,
        0.20274332870257583,
        0.03671529243842253
      ],
      "local_corner_min_m": [
        -0.05280122195555653,
        0.12983962591265696,
        -0.03554227997023818
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07718251646907875,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11331130267340911,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02544491280243906,
      "step_index": 2020,
      "timestamp_seconds": 8.080000383779407,
      "trace_row": 2020,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09797793338907447,
      "vertical_lower_margin_m": 0.10807423059915561,
      "vertical_upper_margin_m": -0.09797793338907447
    },
    {
      "actual_left_finger_qpos_m": [
        0.023513544350862503,
        0.02161160670220852
      ],
      "angular_speed_rps": 0.03451672192575664,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0004244298247946532,
        0.16628718570072742,
        0.0005727000296897877
      ],
      "can_pose": [
        -0.2922166883945465,
        -0.15306134521961212,
        0.9428773522377014,
        0.0037868425715714693,
        0.6998252272605896,
        0.046646762639284134,
        0.7127796411514282
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0042136416417633184,
      "can_relative_translation_from_partial_start_m": [
        0.00031366944313049316,
        -0.0002378225326538086,
        -0.0006600916385650635
      ],
      "can_to_box_relative_orientation_rad": 1.5004981091601213,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0020276308059692383,
        -0.0020276308059692383
      ],
      "left_finger_qf_audit_only": [
        6.798430919647217,
        -6.798439025878906
      ],
      "left_finger_qvel_mps": [
        -0.00038243847666308284,
        3.851647488772869e-05
      ],
      "linear_speed_mps": 0.005109718525728112,
      "local_corner_max_m": [
        0.05194689668427996,
        0.20273443876488662,
        0.03670429828744326
      ],
      "local_corner_min_m": [
        -0.05279575633386924,
        0.12983993263656823,
        -0.035558898228063684
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07719632267348114,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11332792093123462,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025450378424126355,
      "step_index": 2021,
      "timestamp_seconds": 8.084000383969396,
      "trace_row": 2021,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09796904345138525,
      "vertical_lower_margin_m": 0.10807453732306688,
      "vertical_upper_margin_m": -0.09796904345138525
    },
    {
      "actual_left_finger_qpos_m": [
        0.023510895669460297,
        0.021615108475089073
      ],
      "angular_speed_rps": 0.03393388265663557,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0004173290846663513,
        0.16628298680065912,
        0.0005591508082730678
      ],
      "can_pose": [
        -0.292235404253006,
        -0.1530544012784958,
        0.9428752064704895,
        0.003734609577804804,
        0.6998510360717773,
        0.04666930437088013,
        0.7127531170845032
      ],
      "can_relative_orientation_from_partial_start_rad": 0.004344588787382689,
      "can_relative_translation_from_partial_start_m": [
        0.00032061338424682617,
        -0.00023996829986572266,
        -0.0006788074970245361
      ],
      "can_to_box_relative_orientation_rad": 1.500542730078786,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0018649294506758451,
        -0.0018649294506758451
      ],
      "left_finger_qf_audit_only": [
        6.798987865447998,
        -6.7989935874938965
      ],
      "left_finger_qvel_mps": [
        -0.00048547080950811505,
        0.0001475889584980905
      ],
      "linear_speed_mps": 0.005019374679285433,
      "local_corner_max_m": [
        0.05195585562680061,
        0.20272579793638457,
        0.03669350367586155
      ],
      "local_corner_min_m": [
        -0.05279051379613331,
        0.12984017566493367,
        -0.035575202059315414
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07720987189489786,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11334422476248635,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025455620961862283,
      "step_index": 2022,
      "timestamp_seconds": 8.088000384159386,
      "trace_row": 2022,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0979604026228832,
      "vertical_lower_margin_m": 0.10807478035143231,
      "vertical_upper_margin_m": -0.0979604026228832
    },
    {
      "actual_left_finger_qpos_m": [
        0.023508220911026,
        0.02161870151758194
      ],
      "angular_speed_rps": 0.03270725723996286,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00041029798477551505,
        0.16627897486448517,
        0.0005458409830398359
      ],
      "can_pose": [
        -0.2922537624835968,
        -0.15304751694202423,
        0.9428732991218567,
        0.003682733979076147,
        0.6998745203018188,
        0.04669060558080673,
        0.7127289772033691
      ],
      "can_relative_orientation_from_partial_start_rad": 0.004472095729752527,
      "can_relative_translation_from_partial_start_m": [
        0.0003274977207183838,
        -0.00024187564849853516,
        -0.0006971657276153564
      ],
      "can_to_box_relative_orientation_rad": 1.5005886013777237,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.001702228095382452,
        -0.001702228095382452
      ],
      "left_finger_qf_audit_only": [
        6.799543857574463,
        -6.7995476722717285
      ],
      "left_finger_qvel_mps": [
        -0.0005042324773967266,
        0.00019056827295571566
      ],
      "linear_speed_mps": 0.004924788453724657,
      "local_corner_max_m": [
        0.05196464278443294,
        0.20271751209831923,
        0.03668304086748275
      ],
      "local_corner_min_m": [
        -0.05278523875398394,
        0.12984043763065112,
        -0.03559135890140308
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0772231817201311,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11336038160457401,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02546089600401165,
      "step_index": 2023,
      "timestamp_seconds": 8.092000384349376,
      "trace_row": 2023,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09795211678481787,
      "vertical_lower_margin_m": 0.10807504231714976,
      "vertical_upper_margin_m": -0.09795211678481787
    },
    {
      "actual_left_finger_qpos_m": [
        0.02350546233355999,
        0.021622411906719208
      ],
      "angular_speed_rps": 0.032493373117578044,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000403368128599757,
        0.16627454922151363,
        0.00053294265606324
      ],
      "can_pose": [
        -0.2922716736793518,
        -0.15304073691368103,
        0.9428709149360657,
        0.0036315994802862406,
        0.6998980641365051,
        0.04671211913228035,
        0.7127046585083008
      ],
      "can_relative_orientation_from_partial_start_rad": 0.004598798356860553,
      "can_relative_translation_from_partial_start_m": [
        0.00033427774906158447,
        -0.0002442598342895508,
        -0.0007150769233703613
      ],
      "can_to_box_relative_orientation_rad": 1.5006331004135811,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0015395267400890589,
        -0.0015395267400890589
      ],
      "left_finger_qf_audit_only": [
        6.800073623657227,
        -6.800078868865967
      ],
      "left_finger_qvel_mps": [
        -0.0004641209670808166,
        9.61367622949183e-05
      ],
      "linear_speed_mps": 0.004824831760101886,
      "local_corner_max_m": [
        0.051973346186511726,
        0.2027088621746147,
        0.03667294407636401
      ],
      "local_corner_min_m": [
        -0.05278008244371124,
        0.12984023626841257,
        -0.03560705876423753
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07723608004710769,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11337608146740846,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02546605231428435,
      "step_index": 2024,
      "timestamp_seconds": 8.096000384539366,
      "trace_row": 2024,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09794346686111334,
      "vertical_lower_margin_m": 0.10807484095491121,
      "vertical_upper_margin_m": -0.09794346686111334
    },
    {
      "actual_left_finger_qpos_m": [
        0.02350267395377159,
        0.021626053377985954
      ],
      "angular_speed_rps": 0.03235768006568633,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003964890946063504,
        0.16626999019936362,
        0.0005200547704753977
      ],
      "can_pose": [
        -0.2922895848751068,
        -0.1530340164899826,
        0.9428682923316956,
        0.003581160679459572,
        0.6999215483665466,
        0.04673450440168381,
        0.7126803398132324
      ],
      "can_relative_orientation_from_partial_start_rad": 0.004725154850120758,
      "can_relative_translation_from_partial_start_m": [
        0.00034099817276000977,
        -0.00024688243865966797,
        -0.0007329881191253662
      ],
      "can_to_box_relative_orientation_rad": 1.5006753994585733,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0013768253847956657,
        -0.0013768253847956657
      ],
      "left_finger_qf_audit_only": [
        6.800592422485352,
        -6.800600528717041
      ],
      "left_finger_qvel_mps": [
        -0.0005433598416857421,
        0.00021618325263261795
      ],
      "linear_speed_mps": 0.004827350763640183,
      "local_corner_max_m": [
        0.05198207067276289,
        0.2027001804713794,
        0.036662872343117825
      ],
      "local_corner_min_m": [
        -0.05277504886197559,
        0.12983979992734784,
        -0.03562276280216703
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07724896793269553,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11339178550533796,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02547108589602,
      "step_index": 2025,
      "timestamp_seconds": 8.100000384729356,
      "trace_row": 2025,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09793478515787803,
      "vertical_lower_margin_m": 0.10807440461384649,
      "vertical_upper_margin_m": -0.09793478515787803
    },
    {
      "actual_left_finger_qpos_m": [
        0.02349979802966118,
        0.021629858762025833
      ],
      "angular_speed_rps": 0.03130491052154564,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003896656615361982,
        0.1662657491652002,
        0.0005075401677080982
      ],
      "can_pose": [
        -0.2923068702220917,
        -0.15302732586860657,
        0.9428661465644836,
        0.003531397320330143,
        0.6999443173408508,
        0.046753834933042526,
        0.7126568555831909
      ],
      "can_relative_orientation_from_partial_start_rad": 0.004847360268919387,
      "can_relative_translation_from_partial_start_m": [
        0.00034768879413604736,
        -0.00024902820587158203,
        -0.0007502734661102295
      ],
      "can_to_box_relative_orientation_rad": 1.5007209213913912,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0012141240295022726,
        -0.0012141240295022726
      ],
      "left_finger_qf_audit_only": [
        6.801103591918945,
        -6.801113128662109
      ],
      "left_finger_qvel_mps": [
        -0.0004925716202706099,
        0.0001472690491937101
      ],
      "linear_speed_mps": 0.004664707377208138,
      "local_corner_max_m": [
        0.051990486676498776,
        0.20269174311947513,
        0.0366529880243297
      ],
      "local_corner_min_m": [
        -0.0527698179995712,
        0.12983975521092528,
        -0.035637907688913506
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07726148253546283,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11340693039208444,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02547631675842439,
      "step_index": 2026,
      "timestamp_seconds": 8.104000384919345,
      "trace_row": 2026,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09792634780597377,
      "vertical_lower_margin_m": 0.10807435989742392,
      "vertical_upper_margin_m": -0.09792634780597377
    },
    {
      "actual_left_finger_qpos_m": [
        0.023496882990002632,
        0.021633591502904892
      ],
      "angular_speed_rps": 0.031107424835390713,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000382991201411359,
        0.16626123860819308,
        0.0004951908470310906
      ],
      "can_pose": [
        -0.2923239469528198,
        -0.15302078425884247,
        0.9428637027740479,
        0.003482176922261715,
        0.6999672651290894,
        0.046773068606853485,
        0.7126333713531494
      ],
      "can_relative_orientation_from_partial_start_rad": 0.004968794387252332,
      "can_relative_translation_from_partial_start_m": [
        0.0003542304039001465,
        -0.00025147199630737305,
        -0.0007673501968383789
      ],
      "can_to_box_relative_orientation_rad": 1.5007657970578077,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0010514226742088795,
        -0.0010514226742088795
      ],
      "left_finger_qf_audit_only": [
        6.801609992980957,
        -6.801615238189697
      ],
      "left_finger_qvel_mps": [
        -0.0005284084472805262,
        0.00016796693671494722
      ],
      "linear_speed_mps": 0.0046123439677350315,
      "local_corner_max_m": [
        0.051998744888207826,
        0.2026830559290671,
        0.03664321766072104
      ],
      "local_corner_min_m": [
        -0.052764727291030544,
        0.12983942128731907,
        -0.03565283596665886
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07727383185613984,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11342185866982979,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025481407466965048,
      "step_index": 2027,
      "timestamp_seconds": 8.108000385109335,
      "trace_row": 2027,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09791766061556574,
      "vertical_lower_margin_m": 0.10807402597381771,
      "vertical_upper_margin_m": -0.09791766061556574
    },
    {
      "actual_left_finger_qpos_m": [
        0.023493941873311996,
        0.021637486293911934
      ],
      "angular_speed_rps": 0.030530268729028934,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003764719193172228,
        0.1662567268729882,
        0.0004831518605951657
      ],
      "can_pose": [
        -0.29234081506729126,
        -0.1530144214630127,
        0.942861020565033,
        0.003433825680986047,
        0.6999882459640503,
        0.04679485037922859,
        0.7126115560531616
      ],
      "can_relative_orientation_from_partial_start_rad": 0.005089134528586249,
      "can_relative_translation_from_partial_start_m": [
        0.00036059319972991943,
        -0.0002541542053222656,
        -0.0007842183113098145
      ],
      "can_to_box_relative_orientation_rad": 1.50080596570952,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0008887212607078254,
        -0.0008887212607078254
      ],
      "left_finger_qf_audit_only": [
        6.802102565765381,
        -6.80210542678833
      ],
      "left_finger_qvel_mps": [
        -0.0006374212680384517,
        0.000285198912024498
      ],
      "linear_speed_mps": 0.004556675530429842,
      "local_corner_max_m": [
        0.052007059713476134,
        0.202674754432424,
        0.03663402717076614
      ],
      "local_corner_min_m": [
        -0.05276000355211058,
        0.1298386993135524,
        -0.035667723449575806
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07728587084257577,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11343674615274674,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025486131205885013,
      "step_index": 2028,
      "timestamp_seconds": 8.112000385299325,
      "trace_row": 2028,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09790935911892264,
      "vertical_lower_margin_m": 0.10807330400005105,
      "vertical_upper_margin_m": -0.09790935911892264
    },
    {
      "actual_left_finger_qpos_m": [
        0.02349095419049263,
        0.02164141647517681
      ],
      "angular_speed_rps": 0.029860220198484822,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00036987177546646266,
        0.16625217181584684,
        0.0004715368742402304
      ],
      "can_pose": [
        -0.29235708713531494,
        -0.15300796926021576,
        0.9428582787513733,
        0.0033869044855237007,
        0.7000095248222351,
        0.04681548476219177,
        0.7125895023345947
      ],
      "can_relative_orientation_from_partial_start_rad": 0.005206482024013957,
      "can_relative_translation_from_partial_start_m": [
        0.00036704540252685547,
        -0.0002568960189819336,
        -0.0008004903793334961
      ],
      "can_to_box_relative_orientation_rad": 1.500845617836223,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0007260198472067714,
        -0.0007260198472067714
      ],
      "left_finger_qf_audit_only": [
        6.802570343017578,
        -6.802577972412109
      ],
      "left_finger_qvel_mps": [
        -0.000663054408505559,
        0.00030201126355677843
      ],
      "linear_speed_mps": 0.004429507810008588,
      "local_corner_max_m": [
        0.05201536000632623,
        0.2026664046971972,
        0.03662506480573546
      ],
      "local_corner_min_m": [
        -0.05275510355725915,
        0.12983793893449647,
        -0.035681991057255
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0772974858289307,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11345101376042593,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02549103120073644,
      "step_index": 2029,
      "timestamp_seconds": 8.116000385489315,
      "trace_row": 2029,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09790100938369585,
      "vertical_lower_margin_m": 0.10807254362099511,
      "vertical_upper_margin_m": -0.09790100938369585
    },
    {
      "actual_left_finger_qpos_m": [
        0.023487890139222145,
        0.021645398810505867
      ],
      "angular_speed_rps": 0.029196491464572226,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003635097715208313,
        0.1662475166401277,
        0.00046002690974572547
      ],
      "can_pose": [
        -0.2923731207847595,
        -0.15300174057483673,
        0.9428555369377136,
        0.003340194933116436,
        0.7000300288200378,
        0.04683438688516617,
        0.7125682830810547
      ],
      "can_relative_orientation_from_partial_start_rad": 0.005321407214358053,
      "can_relative_translation_from_partial_start_m": [
        0.0003732740879058838,
        -0.00025963783264160156,
        -0.0008165240287780762
      ],
      "can_to_box_relative_orientation_rad": 1.5008873585674691,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.0005633184337057173,
        -0.0005633184337057173
      ],
      "left_finger_qf_audit_only": [
        6.803041458129883,
        -6.803045272827148
      ],
      "left_finger_qvel_mps": [
        -0.0007001459016464651,
        0.0003398118424229324
      ],
      "linear_speed_mps": 0.004354537499739903,
      "local_corner_max_m": [
        0.05202327883367197,
        0.2026579365536143,
        0.03661614442436545
      ],
      "local_corner_min_m": [
        -0.052750298376713634,
        0.12983709672664112,
        -0.035696090604874
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0773089957934252,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11346511330804493,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02549583638128196,
      "step_index": 2030,
      "timestamp_seconds": 8.120000385679305,
      "trace_row": 2030,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09789254124011294,
      "vertical_lower_margin_m": 0.10807170141313976,
      "vertical_upper_margin_m": -0.09789254124011294
    },
    {
      "actual_left_finger_qpos_m": [
        0.023484770208597183,
        0.021649373695254326
      ],
      "angular_speed_rps": 0.02865691447338518,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00035727672195395854,
        0.1662428745154133,
        0.0004487163108059522
      ],
      "can_pose": [
        -0.2923889458179474,
        -0.15299564599990845,
        0.9428527355194092,
        0.003294016234576702,
        0.7000493407249451,
        0.04685377702116966,
        0.7125481963157654
      ],
      "can_relative_orientation_from_partial_start_rad": 0.005434728761136543,
      "can_relative_translation_from_partial_start_m": [
        0.0003793686628341675,
        -0.0002624392509460449,
        -0.0008323490619659424
      ],
      "can_to_box_relative_orientation_rad": 1.50092769274681,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.00040061704930849373,
        -0.00040061704930849373
      ],
      "left_finger_qf_audit_only": [
        6.803487300872803,
        -6.803493976593018
      ],
      "left_finger_qvel_mps": [
        -0.0009150591213256121,
        0.0005380347138270736
      ],
      "linear_speed_mps": 0.004296971574596756,
      "local_corner_max_m": [
        0.0520311093325167,
        0.20264965592408213,
        0.03660751992031608
      ],
      "local_corner_min_m": [
        -0.05274566277642462,
        0.1298360931067445,
        -0.035710087298704174
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07732030639236498,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1134791100018751,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025500471981570974,
      "step_index": 2031,
      "timestamp_seconds": 8.124000385869294,
      "trace_row": 2031,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09788426061058077,
      "vertical_lower_margin_m": 0.10807069779324313,
      "vertical_upper_margin_m": -0.09788426061058077
    },
    {
      "actual_left_finger_qpos_m": [
        0.02348172292113304,
        0.021653372794389725
      ],
      "angular_speed_rps": 0.02818630351808818,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003510402485950581,
        0.1662381526243374,
        0.00043778334981586786
      ],
      "can_pose": [
        -0.29240432381629944,
        -0.15298955142498016,
        0.9428497552871704,
        0.0032490885350853205,
        0.7000687122344971,
        0.04687340930104256,
        0.7125282287597656
      ],
      "can_relative_orientation_from_partial_start_rad": 0.005546134460843612,
      "can_relative_translation_from_partial_start_m": [
        0.00038546323776245117,
        -0.00026541948318481445,
        -0.0008477270603179932
      ],
      "can_to_box_relative_orientation_rad": 1.5009658862575002,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -0.00023791566491127014,
        -0.00023791566491127014
      ],
      "left_finger_qf_audit_only": [
        6.80392599105835,
        -6.803934574127197
      ],
      "left_finger_qvel_mps": [
        -0.0009569608373567462,
        0.0005815498298034072
      ],
      "linear_speed_mps": 0.004201996803844275,
      "local_corner_max_m": [
        0.05203896253423945,
        0.20264139334726272,
        0.03659920806347283
      ],
      "local_corner_min_m": [
        -0.05274104303142957,
        0.12983491190141205,
        -0.0357236413638411
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07733123935335506,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11349266406701203,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025505091726566023,
      "step_index": 2032,
      "timestamp_seconds": 8.128000386059284,
      "trace_row": 2032,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09787599803376136,
      "vertical_lower_margin_m": 0.1080695165879107,
      "vertical_upper_margin_m": -0.09787599803376136
    },
    {
      "actual_left_finger_qpos_m": [
        0.023478519171476364,
        0.021657437086105347
      ],
      "angular_speed_rps": 0.027288347275871053,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00034477310937511274,
        0.16623325663861177,
        0.00042718074766395775
      ],
      "can_pose": [
        -0.2924191951751709,
        -0.1529834121465683,
        0.9428466558456421,
        0.003205031156539917,
        0.700087308883667,
        0.04689132794737816,
        0.7125089764595032
      ],
      "can_relative_orientation_from_partial_start_rad": 0.005654028894697417,
      "can_relative_translation_from_partial_start_m": [
        0.0003916025161743164,
        -0.00026851892471313477,
        -0.0008625984191894531
      ],
      "can_to_box_relative_orientation_rad": 1.5010051729085325,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        -7.521427323808894e-05,
        -7.521427323808894e-05
      ],
      "left_finger_qf_audit_only": [
        6.804342746734619,
        -6.804352283477783
      ],
      "left_finger_qvel_mps": [
        -0.000897453457582742,
        0.0005031671607866883
      ],
      "linear_speed_mps": 0.004096145798093358,
      "local_corner_max_m": [
        0.0520467049636916,
        0.20263297680804826,
        0.036591116497624754
      ],
      "local_corner_min_m": [
        -0.05273625118244185,
        0.12983353646917528,
        -0.03573675500229684
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07734184195550697,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11350577770546777,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02550988357555374,
      "step_index": 2033,
      "timestamp_seconds": 8.132000386249274,
      "trace_row": 2033,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0978675814945469,
      "vertical_lower_margin_m": 0.10806814115567392,
      "vertical_upper_margin_m": -0.0978675814945469
    },
    {
      "actual_left_finger_qpos_m": [
        0.02347521297633648,
        0.02166171185672283
      ],
      "angular_speed_rps": 0.027687339598261442,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003387866335854417,
        0.16622835220061205,
        0.0004167275183021846
      ],
      "can_pose": [
        -0.29243406653404236,
        -0.1529775708913803,
        0.9428434371948242,
        0.00316065875813365,
        0.700105607509613,
        0.04691118374466896,
        0.7124897837638855
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00576382829431539,
      "can_relative_translation_from_partial_start_m": [
        0.0003974437713623047,
        -0.00027173757553100586,
        -0.0008774697780609131
      ],
      "can_to_box_relative_orientation_rad": 1.5010422726356376,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        8.748711843509227e-05,
        8.748711843509227e-05
      ],
      "left_finger_qf_audit_only": [
        6.804762840270996,
        -6.804771900177002
      ],
      "left_finger_qvel_mps": [
        -0.001000577351078391,
        0.0006157630705274642
      ],
      "linear_speed_mps": 0.00407459556818332,
      "local_corner_max_m": [
        0.05205432725283993,
        0.20262466911446675,
        0.036583341152097826
      ],
      "local_corner_min_m": [
        -0.05273190052001081,
        0.12983203528675735,
        -0.03574988611549346
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07735229518486875,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11351890881866439,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02551423423798478,
      "step_index": 2034,
      "timestamp_seconds": 8.136000386439264,
      "trace_row": 2034,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09785927380096539,
      "vertical_lower_margin_m": 0.108066639973256,
      "vertical_upper_margin_m": -0.09785927380096539
    },
    {
      "actual_left_finger_qpos_m": [
        0.0234718956053257,
        0.021665845066308975
      ],
      "angular_speed_rps": 0.026393179217642015,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003327372131588513,
        0.16622358150884464,
        0.00040656408447325987
      ],
      "can_pose": [
        -0.2924484312534332,
        -0.15297165513038635,
        0.9428403377532959,
        0.0031179524958133698,
        0.7001229524612427,
        0.04692956060171127,
        0.7124717831611633
      ],
      "can_relative_orientation_from_partial_start_rad": 0.005868587534622448,
      "can_relative_translation_from_partial_start_m": [
        0.0004033595323562622,
        -0.00027483701705932617,
        -0.0008918344974517822
      ],
      "can_to_box_relative_orientation_rad": 1.5010790059979122,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0002501885173842311,
        0.0002501885173842311
      ],
      "left_finger_qf_audit_only": [
        6.805158615112305,
        -6.805166244506836
      ],
      "left_finger_qvel_mps": [
        -0.0009829113259911537,
        0.0005963888834230602
      ],
      "linear_speed_mps": 0.003960333834293087,
      "local_corner_max_m": [
        0.05206188976886053,
        0.20261661155542798,
        0.03657573603105102
      ],
      "local_corner_min_m": [
        -0.05272736419517826,
        0.1298305514622613,
        -0.0357626078621045
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07736245861869767,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11353163056527543,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02551877056281733,
      "step_index": 2035,
      "timestamp_seconds": 8.140000386629254,
      "trace_row": 2035,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09785121624192662,
      "vertical_lower_margin_m": 0.10806515614875994,
      "vertical_upper_margin_m": -0.09785121624192662
    },
    {
      "actual_left_finger_qpos_m": [
        0.02346857823431492,
        0.021670103073120117
      ],
      "angular_speed_rps": 0.0259565673564657,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003267644981476969,
        0.16621859263049366,
        0.0003964657012669459
      ],
      "can_pose": [
        -0.292462557554245,
        -0.15296579897403717,
        0.942837119102478,
        0.0030758448410779238,
        0.7001407146453857,
        0.046945907175540924,
        0.7124533653259277
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00597122416688737,
      "can_relative_translation_from_partial_start_m": [
        0.00040921568870544434,
        -0.00027805566787719727,
        -0.0009059607982635498
      ],
      "can_to_box_relative_orientation_rad": 1.5011176322259414,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0004128899017814547,
        0.0004128899017814547
      ],
      "left_finger_qf_audit_only": [
        6.805555820465088,
        -6.80556583404541
      ],
      "left_finger_qvel_mps": [
        -0.0009720378438942134,
        0.0006129915127530694
      ],
      "linear_speed_mps": 0.0039067780179100915,
      "local_corner_max_m": [
        0.0520692074850741,
        0.2026082085363874,
        0.036567983204273624
      ],
      "local_corner_min_m": [
        -0.05272273648136949,
        0.12982897672459992,
        -0.03577505180173973
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07737255700190399,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11354407450491066,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0255233982766261,
      "step_index": 2036,
      "timestamp_seconds": 8.144000386819243,
      "trace_row": 2036,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09784281322288603,
      "vertical_lower_margin_m": 0.10806358141109856,
      "vertical_upper_margin_m": -0.09784281322288603
    },
    {
      "actual_left_finger_qpos_m": [
        0.023465212434530258,
        0.02167435735464096
      ],
      "angular_speed_rps": 0.026020464639660696,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00032101419009644694,
        0.16621365478548578,
        0.0003867928334775339
      ],
      "can_pose": [
        -0.2924763858318329,
        -0.1529601812362671,
        0.9428338408470154,
        0.0030335374176502228,
        0.7001575231552124,
        0.04696403816342354,
        0.7124358415603638
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006074654427379428,
      "can_relative_translation_from_partial_start_m": [
        0.0004148334264755249,
        -0.00028133392333984375,
        -0.0009197890758514404
      ],
      "can_to_box_relative_orientation_rad": 1.5011541399581931,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0005755912861786783,
        0.0005755912861786783
      ],
      "left_finger_qf_audit_only": [
        6.805944442749023,
        -6.805952548980713
      ],
      "left_finger_qvel_mps": [
        -0.001135576399974525,
        0.0007230573100969195
      ],
      "linear_speed_mps": 0.0038203989925434134,
      "local_corner_max_m": [
        0.0520764504362734,
        0.20260004195638537,
        0.03656086805109848
      ],
      "local_corner_min_m": [
        -0.052718478816466297,
        0.12982726761458618,
        -0.035787282384143415
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0773822298696934,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11355630508731435,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025527655941529295,
      "step_index": 2037,
      "timestamp_seconds": 8.148000387009233,
      "trace_row": 2037,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09783464664288401,
      "vertical_lower_margin_m": 0.10806187230108483,
      "vertical_upper_margin_m": -0.09783464664288401
    },
    {
      "actual_left_finger_qpos_m": [
        0.023461736738681793,
        0.021678749471902847
      ],
      "angular_speed_rps": 0.02485000705621418,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003152336699282221,
        0.16620872729019998,
        0.00037722966459924345
      ],
      "can_pose": [
        -0.2924899160861969,
        -0.15295451879501343,
        0.9428306221961975,
        0.002992183668538928,
        0.7001729011535645,
        0.046980418264865875,
        0.712419867515564
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006173588650896157,
      "can_relative_translation_from_partial_start_m": [
        0.000420495867729187,
        -0.00028455257415771484,
        -0.0009333193302154541
      ],
      "can_to_box_relative_orientation_rad": 1.501191696214428,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0007382926996797323,
        0.0007382926996797323
      ],
      "left_finger_qf_audit_only": [
        6.806314945220947,
        -6.806324481964111
      ],
      "left_finger_qvel_mps": [
        -0.0010810540989041328,
        0.0006937121506780386
      ],
      "linear_speed_mps": 0.0037540870708885296,
      "local_corner_max_m": [
        0.05208357887796938,
        0.20259197918323968,
        0.03655380787360479
      ],
      "local_corner_min_m": [
        -0.05271404621782583,
        0.12982547539716027,
        -0.035799348544406306
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07739179303857169,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11356837124757724,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025532088540169764,
      "step_index": 2038,
      "timestamp_seconds": 8.152000387199223,
      "trace_row": 2038,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09782658386973832,
      "vertical_lower_margin_m": 0.10806008008365892,
      "vertical_upper_margin_m": -0.09782658386973832
    },
    {
      "actual_left_finger_qpos_m": [
        0.023458274081349373,
        0.021683137863874435
      ],
      "angular_speed_rps": 0.024996859294325262,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003095560913714268,
        0.1662035136252752,
        0.00036785312067927345
      ],
      "can_pose": [
        -0.292503297328949,
        -0.15294897556304932,
        0.9428269267082214,
        0.002952022710815072,
        0.7001892328262329,
        0.04699850454926491,
        0.7124027609825134
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0062729256833308055,
      "can_relative_translation_from_partial_start_m": [
        0.00042603909969329834,
        -0.00028824806213378906,
        -0.0009467005729675293
      ],
      "can_to_box_relative_orientation_rad": 1.5012251503785348,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0009009941131807864,
        0.0009009941131807864
      ],
      "left_finger_qf_audit_only": [
        6.806674003601074,
        -6.806682109832764
      ],
      "left_finger_qvel_mps": [
        -0.0012517469003796577,
        0.000846425537019968
      ],
      "linear_speed_mps": 0.003736991506825692,
      "local_corner_max_m": [
        0.05209074535643249,
        0.20258371460287428,
        0.036546881408019316
      ],
      "local_corner_min_m": [
        -0.05270985753917534,
        0.1298233126476761,
        -0.03581117516666077
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07740116958249166,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1135801978698317,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02553627721882025,
      "step_index": 2039,
      "timestamp_seconds": 8.156000387389213,
      "trace_row": 2039,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09781831928937292,
      "vertical_lower_margin_m": 0.10805791733417475,
      "vertical_upper_margin_m": -0.09781831928937292
    },
    {
      "actual_left_finger_qpos_m": [
        0.023454664275050163,
        0.021687595173716545
      ],
      "angular_speed_rps": 0.02431664847490675,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003039039698050361,
        0.16619842995572442,
        0.0003587273594101159
      ],
      "can_pose": [
        -0.29251641035079956,
        -0.1529434621334076,
        0.9428232908248901,
        0.002912404015660286,
        0.7002038955688477,
        0.04701700434088707,
        0.7123873233795166
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006369929334673606,
      "can_relative_translation_from_partial_start_m": [
        0.00043155252933502197,
        -0.0002918839454650879,
        -0.0009598135948181152
      ],
      "can_to_box_relative_orientation_rad": 1.5012572967479167,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0010636955266818404,
        0.0010636955266818404
      ],
      "left_finger_qf_audit_only": [
        6.807026386260986,
        -6.807036399841309
      ],
      "left_finger_qvel_mps": [
        -0.001160124782472849,
        0.0007504032691940665
      ],
      "linear_speed_mps": 0.0036705659950906485,
      "local_corner_max_m": [
        0.05209792083425699,
        0.20257579867609976,
        0.03654033988678318
      ],
      "local_corner_min_m": [
        -0.05270572877386703,
        0.1298210612353491,
        -0.03582288516796295
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07741029534376082,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11359190787113388,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02554040598412856,
      "step_index": 2040,
      "timestamp_seconds": 8.160000387579203,
      "trace_row": 2040,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0978104033625984,
      "vertical_lower_margin_m": 0.10805566592184773,
      "vertical_upper_margin_m": -0.0978104033625984
    },
    {
      "actual_left_finger_qpos_m": [
        0.023451173678040504,
        0.021692050620913506
      ],
      "angular_speed_rps": 0.024145831488911626,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00029845395041364076,
        0.16619333172476325,
        0.00034979646842120404
      ],
      "can_pose": [
        -0.2925291657447815,
        -0.1529381275177002,
        0.9428198337554932,
        0.0028726293239742517,
        0.7002193927764893,
        0.04703284427523613,
        0.7123712301254272
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006465944893463861,
      "can_relative_translation_from_partial_start_m": [
        0.00043688714504241943,
        -0.00029534101486206055,
        -0.0009725689888000488
      ],
      "can_to_box_relative_orientation_rad": 1.5012932958103313,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0012263968819752336,
        0.0012263968819752336
      ],
      "left_finger_qf_audit_only": [
        6.807365894317627,
        -6.807375431060791
      ],
      "left_finger_qvel_mps": [
        -0.0013362925965338945,
        0.0009485119371674955
      ],
      "linear_speed_mps": 0.0035629123436898133,
      "local_corner_max_m": [
        0.05210467354412576,
        0.20256762161307496,
        0.03653375955699645
      ],
      "local_corner_min_m": [
        -0.052701581444953016,
        0.12981904183645154,
        -0.03583416662015404
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07741922623474973,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11360318932332497,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025544553313042576,
      "step_index": 2041,
      "timestamp_seconds": 8.164000387769192,
      "trace_row": 2041,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0978022262995736,
      "vertical_lower_margin_m": 0.10805364652295019,
      "vertical_upper_margin_m": -0.0978022262995736
    },
    {
      "actual_left_finger_qpos_m": [
        0.023447586223483086,
        0.021696530282497406
      ],
      "angular_speed_rps": 0.02354422444533534,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00029290024540085113,
        0.1661882320529019,
        0.0003411250932848775
      ],
      "can_pose": [
        -0.2925416827201843,
        -0.15293270349502563,
        0.9428161978721619,
        0.0028339182026684284,
        0.700233519077301,
        0.04705018550157547,
        0.712356448173523
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006559912760530316,
      "can_relative_translation_from_partial_start_m": [
        0.00044231116771698,
        -0.0002989768981933594,
        -0.0009850859642028809
      ],
      "can_to_box_relative_orientation_rad": 1.5013257289449637,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0013890982372686267,
        0.0013890982372686267
      ],
      "left_finger_qf_audit_only": [
        6.807701587677002,
        -6.807713985443115
      ],
      "left_finger_qvel_mps": [
        -0.0012696631019935012,
        0.0008394578471779823
      ],
      "linear_speed_mps": 0.003529468124539274,
      "local_corner_max_m": [
        0.05211165436178525,
        0.2025597321086947,
        0.036527584014201864
      ],
      "local_corner_min_m": [
        -0.05269745485258698,
        0.12981673199710908,
        -0.03584533382763211
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07742789760988605,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11361435653080304,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025548679905408614,
      "step_index": 2042,
      "timestamp_seconds": 8.168000387959182,
      "trace_row": 2042,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09779433679519335,
      "vertical_lower_margin_m": 0.10805133668360772,
      "vertical_upper_margin_m": -0.09779433679519335
    },
    {
      "actual_left_finger_qpos_m": [
        0.02344393916428089,
        0.021701058372855186
      ],
      "angular_speed_rps": 0.022981444544929605,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00028750575194361194,
        0.1661829860503945,
        0.0003326399909296396
      ],
      "can_pose": [
        -0.2925538718700409,
        -0.152927428483963,
        0.942812442779541,
        0.0027960732113569975,
        0.7002476453781128,
        0.04706627130508423,
        0.7123415470123291
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006651527865037069,
      "can_relative_translation_from_partial_start_m": [
        0.00044758617877960205,
        -0.000302731990814209,
        -0.0009972751140594482
      ],
      "can_to_box_relative_orientation_rad": 1.501358608172425,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0015517995925620198,
        0.0015517995925620198
      ],
      "left_finger_qf_audit_only": [
        6.808026313781738,
        -6.808038234710693
      ],
      "left_finger_qvel_mps": [
        -0.0012506793718785048,
        0.0008654601406306028
      ],
      "linear_speed_mps": 0.0034505599041233415,
      "local_corner_max_m": [
        0.052118372439554195,
        0.2025516686772062,
        0.036521447583389266
      ],
      "local_corner_min_m": [
        -0.05269338394344142,
        0.1298143034235828,
        -0.03585616760152999
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07743638271224129,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11362519030470092,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025552750814554173,
      "step_index": 2043,
      "timestamp_seconds": 8.172000388149172,
      "trace_row": 2043,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09778627336370484,
      "vertical_lower_margin_m": 0.10804890811008144,
      "vertical_upper_margin_m": -0.09778627336370484
    },
    {
      "actual_left_finger_qpos_m": [
        0.023440219461917877,
        0.021705670282244682
      ],
      "angular_speed_rps": 0.02317417834748931,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00028209114486202336,
        0.16617787511910442,
        0.00032421628995460416
      ],
      "can_pose": [
        -0.29256606101989746,
        -0.1529221385717392,
        0.9428088068962097,
        0.0027578738518059254,
        0.700261652469635,
        0.04708293825387955,
        0.7123268842697144
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006744002002185755,
      "can_relative_translation_from_partial_start_m": [
        0.00045287609100341797,
        -0.0003063678741455078,
        -0.0010094642639160156
      ],
      "can_to_box_relative_orientation_rad": 1.5013912258488287,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.001714500947855413,
        0.001714500947855413
      ],
      "left_finger_qf_audit_only": [
        6.808350086212158,
        -6.808359622955322
      ],
      "left_finger_qvel_mps": [
        -0.001257598865777254,
        0.0008436946664005518
      ],
      "linear_speed_mps": 0.003443999992127529,
      "local_corner_max_m": [
        0.052125158114531306,
        0.20254377001500012,
        0.03651544976713389
      ],
      "local_corner_min_m": [
        -0.052689340404255325,
        0.12981198022320872,
        -0.03586701718722468
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07744480641321633,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11363603989039561,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025556794353740267,
      "step_index": 2044,
      "timestamp_seconds": 8.176000388339162,
      "trace_row": 2044,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09777837470149876,
      "vertical_lower_margin_m": 0.10804658490970737,
      "vertical_upper_margin_m": -0.09777837470149876
    },
    {
      "actual_left_finger_qpos_m": [
        0.023436469957232475,
        0.021710339933633804
      ],
      "angular_speed_rps": 0.02242132495270718,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00027697071781357385,
        0.1661726454510386,
        0.00031615759216480077
      ],
      "can_pose": [
        -0.2925778031349182,
        -0.15291714668273926,
        0.9428049325942993,
        0.0027211285196244717,
        0.7002748847007751,
        0.047099899500608444,
        0.7123128175735474
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0068335267178236845,
      "can_relative_translation_from_partial_start_m": [
        0.00045786798000335693,
        -0.0003102421760559082,
        -0.0010212063789367676
      ],
      "can_to_box_relative_orientation_rad": 1.501421331891581,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.001877202303148806,
        0.001877202303148806
      ],
      "left_finger_qf_audit_only": [
        6.808663845062256,
        -6.80867338180542
      ],
      "left_finger_qvel_mps": [
        -0.0014585615135729313,
        0.001054253545589745
      ],
      "linear_speed_mps": 0.00333360183726353,
      "local_corner_max_m": [
        0.05213167452164594,
        0.2025359300385955,
        0.0365097993388408
      ],
      "local_corner_min_m": [
        -0.05268561595727306,
        0.12980936086348172,
        -0.0358774841545112
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07745286511100613,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11364650685768213,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025560518800722534,
      "step_index": 2045,
      "timestamp_seconds": 8.180000388529152,
      "trace_row": 2045,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09777053472509413,
      "vertical_lower_margin_m": 0.10804396554998036,
      "vertical_upper_margin_m": -0.09777053472509413
    },
    {
      "actual_left_finger_qpos_m": [
        0.023432791233062744,
        0.021714922040700912
      ],
      "angular_speed_rps": 0.0215784120947461,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00027172126825553145,
        0.16616723682306478,
        0.00030835255339456413
      ],
      "can_pose": [
        -0.29258909821510315,
        -0.15291200578212738,
        0.9428009986877441,
        0.0026849093846976757,
        0.7002875208854675,
        0.0471145398914814,
        0.7122995257377625
      ],
      "can_relative_orientation_from_partial_start_rad": 0.006919659901969423,
      "can_relative_translation_from_partial_start_m": [
        0.0004630088806152344,
        -0.000314176082611084,
        -0.001032501459121704
      ],
      "can_to_box_relative_orientation_rad": 1.5014538674521243,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.002039903774857521,
        0.002039903774857521
      ],
      "left_finger_qf_audit_only": [
        6.808955192565918,
        -6.808968544006348
      ],
      "left_finger_qvel_mps": [
        -0.0014627000782638788,
        0.0010293959639966488
      ],
      "linear_speed_mps": 0.003254643799348023,
      "local_corner_max_m": [
        0.05213812781588306,
        0.20252786530450229,
        0.03650426900710019
      ],
      "local_corner_min_m": [
        -0.052681570352394125,
        0.12980660834162727,
        -0.03588756390031106
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07746067014977637,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11365658660348199,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025564564405601467,
      "step_index": 2046,
      "timestamp_seconds": 8.184000388719141,
      "trace_row": 2046,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09776246999100092,
      "vertical_lower_margin_m": 0.10804121302812592,
      "vertical_upper_margin_m": -0.09776246999100092
    },
    {
      "actual_left_finger_qpos_m": [
        0.023429017513990402,
        0.021719591692090034
      ],
      "angular_speed_rps": 0.02163376057596007,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00026659919220820005,
        0.1661621305892863,
        0.00030060814422017135
      ],
      "can_pose": [
        -0.2926003634929657,
        -0.15290699899196625,
        0.9427973031997681,
        0.0026489393785595894,
        0.7003002762794495,
        0.04712989181280136,
        0.712286114692688
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00700604734823326,
      "can_relative_translation_from_partial_start_m": [
        0.0004680156707763672,
        -0.0003178715705871582,
        -0.001043766736984253
      ],
      "can_to_box_relative_orientation_rad": 1.5014850684618997,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.002202605130150914,
        0.002202605130150914
      ],
      "left_finger_qf_audit_only": [
        6.809249401092529,
        -6.809263706207275
      ],
      "left_finger_qvel_mps": [
        -0.0014995784731581807,
        0.001079976442269981
      ],
      "linear_speed_mps": 0.0032174431685467702,
      "local_corner_max_m": [
        0.05214451230566472,
        0.2025201517870071,
        0.03649882029822099
      ],
      "local_corner_min_m": [
        -0.05267771069008109,
        0.1298041093915655,
        -0.03589760400978065
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07746841455895076,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11366662671295158,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0255684240679145,
      "step_index": 2047,
      "timestamp_seconds": 8.188000388909131,
      "trace_row": 2047,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09775475647350575,
      "vertical_lower_margin_m": 0.10803871407806415,
      "vertical_upper_margin_m": -0.09775475647350575
    },
    {
      "actual_left_finger_qpos_m": [
        0.023425234481692314,
        0.021724343299865723
      ],
      "angular_speed_rps": 0.020824278297979427,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002615376862402097,
        0.1661567788753715,
        0.00029319942170719093
      ],
      "can_pose": [
        -0.2926112115383148,
        -0.1529020518064499,
        0.9427933096885681,
        0.002613881602883339,
        0.7003116607666016,
        0.047145042568445206,
        0.7122740149497986
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0070893130130117105,
      "can_relative_translation_from_partial_start_m": [
        0.0004729628562927246,
        -0.0003218650817871094,
        -0.001054614782333374
      ],
      "can_to_box_relative_orientation_rad": 1.501515246937072,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0023653064854443073,
        0.0023653064854443073
      ],
      "left_finger_qf_audit_only": [
        6.809535026550293,
        -6.8095526695251465
      ],
      "left_finger_qvel_mps": [
        -0.0015048719942569733,
        0.0010805055499076843
      ],
      "linear_speed_mps": 0.0031434738856380567,
      "local_corner_max_m": [
        0.052150820030143846,
        0.20251236640448933,
        0.03649374787814247
      ],
      "local_corner_min_m": [
        -0.05267389540262424,
        0.12980119134625367,
        -0.03590734903472809
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07747582328146374,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11367637173789902,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025572239355371354,
      "step_index": 2048,
      "timestamp_seconds": 8.192000389099121,
      "trace_row": 2048,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09774697109098797,
      "vertical_lower_margin_m": 0.10803579603275232,
      "vertical_upper_margin_m": -0.09774697109098797
    },
    {
      "actual_left_finger_qpos_m": [
        0.023421304300427437,
        0.021729083731770515
      ],
      "angular_speed_rps": 0.020809218045770548,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002565586539074738,
        0.1661515709146072,
        0.0002859804330904714
      ],
      "can_pose": [
        -0.2926218807697296,
        -0.1528971940279007,
        0.9427893757820129,
        0.002579383086413145,
        0.7003234028816223,
        0.04716091230511665,
        0.7122616767883301
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0071725008310936445,
      "can_relative_translation_from_partial_start_m": [
        0.00047782063484191895,
        -0.00032579898834228516,
        -0.001065284013748169
      ],
      "can_to_box_relative_orientation_rad": 1.5015436288344561,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0025280078407377005,
        0.0025280078407377005
      ],
      "left_finger_qf_audit_only": [
        6.809803009033203,
        -6.809817314147949
      ],
      "left_finger_qvel_mps": [
        -0.0015706964768469334,
        0.0011307094246149063
      ],
      "linear_speed_mps": 0.0030913803316137394,
      "local_corner_max_m": [
        0.05215710412785868,
        0.20250477682075374,
        0.03648885064513857
      ],
      "local_corner_min_m": [
        -0.052670221435673625,
        0.12979836500846065,
        -0.03591688977895763
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07748304227008046,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11368591248212856,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025575913322321966,
      "step_index": 2049,
      "timestamp_seconds": 8.196000389289111,
      "trace_row": 2049,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09773938150725238,
      "vertical_lower_margin_m": 0.10803296969495929,
      "vertical_upper_margin_m": -0.09773938150725238
    },
    {
      "actual_left_finger_qpos_m": [
        0.023417487740516663,
        0.021733837202191353
      ],
      "angular_speed_rps": 0.02033498125678857,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002516824726591371,
        0.16614615147517287,
        0.0002788378350990772
      ],
      "can_pose": [
        -0.29263225197792053,
        -0.15289241075515747,
        0.9427854418754578,
        0.0025450182147324085,
        0.7003356218338013,
        0.04717354476451874,
        0.7122488617897034
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007253508603506676,
      "can_relative_translation_from_partial_start_m": [
        0.00048260390758514404,
        -0.00032973289489746094,
        -0.001075655221939087
      ],
      "can_to_box_relative_orientation_rad": 1.5015762245609847,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0026907091960310936,
        0.0026907091960310936
      ],
      "left_finger_qf_audit_only": [
        6.810067653656006,
        -6.8100810050964355
      ],
      "left_finger_qvel_mps": [
        -0.0016547085251659155,
        0.001211178139783442
      ],
      "linear_speed_mps": 0.003019905466224299,
      "local_corner_max_m": [
        0.052163017773784154,
        0.20249673795727852,
        0.036483761524296
      ],
      "local_corner_min_m": [
        -0.0526663827191024,
        0.12979556499306721,
        -0.035926085854097844
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07749018486807185,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11369510855726878,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02557975203889319,
      "step_index": 2050,
      "timestamp_seconds": 8.2000003894791,
      "trace_row": 2050,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09773134264377716,
      "vertical_lower_margin_m": 0.10803016967956586,
      "vertical_upper_margin_m": -0.09773134264377716
    },
    {
      "actual_left_finger_qpos_m": [
        0.023413529619574547,
        0.02173870988190174
      ],
      "angular_speed_rps": 0.019998919592489842,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00024673197207514264,
        0.1661407747240543,
        0.00027184813640535044
      ],
      "can_pose": [
        -0.29264262318611145,
        -0.15288758277893066,
        0.9427812695503235,
        0.0025114482268691063,
        0.7003456950187683,
        0.04718943312764168,
        0.7122379541397095
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0073334899798208055,
      "can_relative_translation_from_partial_start_m": [
        0.0004874318838119507,
        -0.0003339052200317383,
        -0.0010860264301300049
      ],
      "can_to_box_relative_orientation_rad": 1.5016032594387263,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0028534105513244867,
        0.0028534105513244867
      ],
      "left_finger_qf_audit_only": [
        6.810318946838379,
        -6.810337066650391
      ],
      "left_finger_qvel_mps": [
        -0.0016029422404244542,
        0.0011752969585359097
      ],
      "linear_speed_mps": 0.0030442527482771767,
      "local_corner_max_m": [
        0.05216927566841953,
        0.20248918808291205,
        0.03647916596517825
      ],
      "local_corner_min_m": [
        -0.05266273961256984,
        0.12979236136519656,
        -0.03593546969236755
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07749717456676558,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11370449239553848,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02558339514542575,
      "step_index": 2051,
      "timestamp_seconds": 8.20400038966909,
      "trace_row": 2051,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09772379276941069,
      "vertical_lower_margin_m": 0.1080269660516952,
      "vertical_upper_margin_m": -0.09772379276941069
    },
    {
      "actual_left_finger_qpos_m": [
        0.02340121939778328,
        0.021752677857875824
      ],
      "angular_speed_rps": 0.05334497306202165,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00024323026924835678,
        0.1661651828384958,
        0.0002655568367238015
      ],
      "can_pose": [
        -0.29265400767326355,
        -0.15288396179676056,
        0.9428117871284485,
        0.0024252720177173615,
        0.7003016471862793,
        0.04718134179711342,
        0.712282121181488
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007427930255518268,
      "can_relative_translation_from_partial_start_m": [
        0.0004910528659820557,
        -0.0003033876419067383,
        -0.0010974109172821045
      ],
      "can_to_box_relative_orientation_rad": 1.5017412908459682,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.00301611190661788,
        0.00301611190661788
      ],
      "left_finger_qf_audit_only": [
        6.810575485229492,
        -6.8105878829956055
      ],
      "left_finger_qvel_mps": [
        0.0021452719811350107,
        -0.0032245684415102005
      ],
      "linear_speed_mps": 0.008193139402037993,
      "local_corner_max_m": [
        0.05217210682024964,
        0.20251171656837463,
        0.03648179100869453
      ],
      "local_corner_min_m": [
        -0.052658567358746355,
        0.12981864910861696,
        -0.03595067733524693
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07750346586644713,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11371970003841786,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025581758421754905,
      "step_index": 2052,
      "timestamp_seconds": 8.20800038985908,
      "trace_row": 2052,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09774632125487327,
      "vertical_lower_margin_m": 0.1080532537951156,
      "vertical_upper_margin_m": -0.09774632125487327
    },
    {
      "actual_left_finger_qpos_m": [
        0.023401746526360512,
        0.02175166830420494
      ],
      "angular_speed_rps": 0.02455063355947439,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002387589198626916,
        0.1661647157131404,
        0.0002577760949386554
      ],
      "can_pose": [
        -0.29266244173049927,
        -0.1528792530298233,
        0.9428152441978455,
        0.0023926689755171537,
        0.7003218531608582,
        0.047156572341918945,
        0.7122640609741211
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007484948946576667,
      "can_relative_translation_from_partial_start_m": [
        0.0004957616329193115,
        -0.0002999305725097656,
        -0.0011058449745178223
      ],
      "can_to_box_relative_orientation_rad": 1.5018223192631415,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.003178813261911273,
        0.003178813261911273
      ],
      "left_finger_qf_audit_only": [
        6.809765338897705,
        -6.809775352478027
      ],
      "left_finger_qvel_mps": [
        -0.000630868598818779,
        0.00023647827038075775
      ],
      "linear_speed_mps": 0.002564872393772147,
      "local_corner_max_m": [
        0.052174517487646954,
        0.20250578550622633,
        0.03647285152836327
      ],
      "local_corner_min_m": [
        -0.05265203532737234,
        0.12982364592005446,
        -0.03595729933848596
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07751124660823228,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11372632204165689,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025579347754357593,
      "step_index": 2053,
      "timestamp_seconds": 8.21200039004907,
      "trace_row": 2053,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09774039019272497,
      "vertical_lower_margin_m": 0.10805825060655311,
      "vertical_upper_margin_m": -0.09774039019272497
    },
    {
      "actual_left_finger_qpos_m": [
        0.02340025268495083,
        0.021754728630185127
      ],
      "angular_speed_rps": 0.02769521296191463,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00023394612203281318,
        0.16616202659874335,
        0.00024938992515805003
      ],
      "can_pose": [
        -0.2926757335662842,
        -0.15287476778030396,
        0.9428122043609619,
        0.002359436359256506,
        0.7003358006477356,
        0.04719540849328041,
        0.712247908115387
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007585850636068585,
      "can_relative_translation_from_partial_start_m": [
        0.0005002468824386597,
        -0.00030297040939331055,
        -0.0011191368103027344
      ],
      "can_to_box_relative_orientation_rad": 1.5018173731892928,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.003341514617204666,
        0.003341514617204666
      ],
      "left_finger_qf_audit_only": [
        6.810179710388184,
        -6.810189247131348
      ],
      "left_finger_qvel_mps": [
        -0.0009625285165384412,
        0.000634445168543607
      ],
      "linear_speed_mps": 0.003588444566335047,
      "local_corner_max_m": [
        0.052182534550034104,
        0.202501941464719,
        0.03646799737784612
      ],
      "local_corner_min_m": [
        -0.0526504267940997,
        0.1298221117327677,
        -0.03596921752753002
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07751963277801288,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11373824023070095,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025571330691970443,
      "step_index": 2054,
      "timestamp_seconds": 8.21600039023906,
      "trace_row": 2054,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09773654615121764,
      "vertical_lower_margin_m": 0.10805671641926634,
      "vertical_upper_margin_m": -0.09773654615121764
    },
    {
      "actual_left_finger_qpos_m": [
        0.02339732088148594,
        0.02175852097570896
      ],
      "angular_speed_rps": 0.02070841241494332,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002294498691915725,
        0.16615856566945864,
        0.0002425221364942276
      ],
      "can_pose": [
        -0.2926860451698303,
        -0.15287041664123535,
        0.9428097009658813,
        0.0023274102713912725,
        0.7003487348556519,
        0.0472136065363884,
        0.7122340798377991
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007667842871419603,
      "can_relative_translation_from_partial_start_m": [
        0.0005045980215072632,
        -0.00030547380447387695,
        -0.001129448413848877
      ],
      "can_to_box_relative_orientation_rad": 1.501838935753103,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0035042159724980593,
        0.0035042159724980593
      ],
      "left_finger_qf_audit_only": [
        6.810498237609863,
        -6.810509204864502
      ],
      "left_finger_qvel_mps": [
        -0.0013846780639141798,
        0.0008913388010114431
      ],
      "linear_speed_mps": 0.0028671474644017887,
      "local_corner_max_m": [
        0.05218852763397547,
        0.20249627625598388,
        0.036463329223833774
      ],
      "local_corner_min_m": [
        -0.05264742737235861,
        0.1298208550829334,
        -0.03597828495084532
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0775265005666767,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11374730765401625,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02556533760802908,
      "step_index": 2055,
      "timestamp_seconds": 8.22000039042905,
      "trace_row": 2055,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09773088094248251,
      "vertical_lower_margin_m": 0.10805545976943204,
      "vertical_upper_margin_m": -0.09773088094248251
    },
    {
      "actual_left_finger_qpos_m": [
        0.023393863812088966,
        0.02176283299922943
      ],
      "angular_speed_rps": 0.01858192927103524,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002249609947899689,
        0.16615428407175103,
        0.00023640211361380947
      ],
      "can_pose": [
        -0.29269376397132874,
        -0.15286584198474884,
        0.9428080320358276,
        0.0022970610298216343,
        0.700363278388977,
        0.047205716371536255,
        0.7122204303741455
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007728473805342005,
      "can_relative_translation_from_partial_start_m": [
        0.0005091726779937744,
        -0.0003071427345275879,
        -0.00113716721534729
      ],
      "can_to_box_relative_orientation_rad": 1.5018937145165243,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0036669173277914524,
        0.0036669173277914524
      ],
      "left_finger_qf_audit_only": [
        6.810796737670898,
        -6.8108110427856445
      ],
      "left_finger_qvel_mps": [
        -0.0014981181593611836,
        0.0010465143714100122
      ],
      "linear_speed_mps": 0.002281620834972381,
      "local_corner_max_m": [
        0.05219235440222081,
        0.20248820545709678,
        0.036457472888070996
      ],
      "local_corner_min_m": [
        -0.052642276391800746,
        0.1298203626864053,
        -0.03598466866084338
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07753262058955712,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11375369136401431,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025561510839783738,
      "step_index": 2056,
      "timestamp_seconds": 8.22400039061904,
      "trace_row": 2056,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09772281014359542,
      "vertical_lower_margin_m": 0.10805496737290393,
      "vertical_upper_margin_m": -0.09772281014359542
    },
    {
      "actual_left_finger_qpos_m": [
        0.023390013724565506,
        0.02176765352487564
      ],
      "angular_speed_rps": 0.020712766431456933,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00022038823654196849,
        0.16615017992326098,
        0.00023095289379199135
      ],
      "can_pose": [
        -0.29270270466804504,
        -0.15286143124103546,
        0.9428046941757202,
        0.00226608756929636,
        0.7003761529922485,
        0.0472257100045681,
        0.7122066020965576
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007809951246674023,
      "can_relative_translation_from_partial_start_m": [
        0.0005135834217071533,
        -0.00031048059463500977,
        -0.0011461079120635986
      ],
      "can_to_box_relative_orientation_rad": 1.501911292967014,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0038296186830848455,
        0.0038296186830848455
      ],
      "left_finger_qf_audit_only": [
        6.811093807220459,
        -6.8111066818237305
      ],
      "left_finger_qvel_mps": [
        -0.0013853777199983597,
        0.0009565082145854831
      ],
      "linear_speed_mps": 0.0026283552066223696,
      "local_corner_max_m": [
        0.05219857237606662,
        0.20248207921887973,
        0.03645427702891024
      ],
      "local_corner_min_m": [
        -0.05263934884915056,
        0.12981828062764222,
        -0.03599237124132626
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07753806980937894,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11376139394449719,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025555292865937926,
      "step_index": 2057,
      "timestamp_seconds": 8.22800039080903,
      "trace_row": 2057,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09771668390537837,
      "vertical_lower_margin_m": 0.10805288531414087,
      "vertical_upper_margin_m": -0.09771668390537837
    },
    {
      "actual_left_finger_qpos_m": [
        0.023386016488075256,
        0.021772561594843864
      ],
      "angular_speed_rps": 0.01974302450846565,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002160978134853886,
        0.166145802592496,
        0.00022566894406644833
      ],
      "can_pose": [
        -0.2927112877368927,
        -0.15285728871822357,
        0.9428011178970337,
        0.0022362738382071257,
        0.7003886103630066,
        0.04724401980638504,
        0.7121931910514832
      ],
      "can_relative_orientation_from_partial_start_rad": 0.007887803451257938,
      "can_relative_translation_from_partial_start_m": [
        0.000517725944519043,
        -0.0003140568733215332,
        -0.0011546909809112549
      ],
      "can_to_box_relative_orientation_rad": 1.501929488668834,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.003992320038378239,
        0.003992320038378239
      ],
      "left_finger_qf_audit_only": [
        6.811389923095703,
        -6.811404228210449
      ],
      "left_finger_qvel_mps": [
        -0.0015696040354669094,
        0.0011001760140061378
      ],
      "linear_speed_mps": 0.0025448394533227328,
      "local_corner_max_m": [
        0.05220436912207729,
        0.2024756895132379,
        0.03645109173964994
      ],
      "local_corner_min_m": [
        -0.0526365647490481,
        0.1298159156717541,
        -0.03599975385151705
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07754335375910448,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11376877655468798,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025549496119927254,
      "step_index": 2058,
      "timestamp_seconds": 8.23200039099902,
      "trace_row": 2058,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09771029419973655,
      "vertical_lower_margin_m": 0.10805052035825274,
      "vertical_upper_margin_m": -0.09771029419973655
    },
    {
      "actual_left_finger_qpos_m": [
        0.023381898179650307,
        0.02177749201655388
      ],
      "angular_speed_rps": 0.017225423834907622,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00021181648454227098,
        0.16614109768209995,
        0.00022049663166023858
      ],
      "can_pose": [
        -0.2927185297012329,
        -0.15285299718379974,
        0.942798376083374,
        0.002207111334428191,
        0.7004017233848572,
        0.04724450409412384,
        0.7121803760528564
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00795149413775396,
      "can_relative_translation_from_partial_start_m": [
        0.0005220174789428711,
        -0.00031679868698120117,
        -0.0011619329452514648
      ],
      "can_to_box_relative_orientation_rad": 1.5019711140541776,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0041550216265022755,
        0.0041550216265022755
      ],
      "left_finger_qf_audit_only": [
        6.811670303344727,
        -6.811685562133789
      ],
      "left_finger_qvel_mps": [
        -0.0016593292821198702,
        0.0011935846414417028
      ],
      "linear_speed_mps": 0.002213323997892296,
      "local_corner_max_m": [
        0.05220868164730208,
        0.2024679008528898,
        0.036446767107243705
      ],
      "local_corner_min_m": [
        -0.05263231461638662,
        0.1298142945113101,
        -0.03600577384392323
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07754852607151069,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11377479654709416,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025545183594702467,
      "step_index": 2059,
      "timestamp_seconds": 8.236000391189009,
      "trace_row": 2059,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09770250553938843,
      "vertical_lower_margin_m": 0.10804889919780875,
      "vertical_upper_margin_m": -0.09770250553938843
    },
    {
      "actual_left_finger_qpos_m": [
        0.02337777614593506,
        0.021782610565423965
      ],
      "angular_speed_rps": 0.018175541139547113,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00020749438998485248,
        0.16613687127637655,
        0.0002157129601749741
      ],
      "can_pose": [
        -0.29272621870040894,
        -0.15284878015518188,
        0.9427952170372009,
        0.0021782545372843742,
        0.7004138827323914,
        0.047257907688617706,
        0.7121676802635193
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008023596110444866,
      "can_relative_translation_from_partial_start_m": [
        0.00052623450756073,
        -0.0003199577331542969,
        -0.0011696219444274902
      ],
      "can_to_box_relative_orientation_rad": 1.5019946430892825,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.004317723214626312,
        0.004317723214626312
      ],
      "left_finger_qf_audit_only": [
        6.811944007873535,
        -6.811957836151123
      ],
      "left_finger_qvel_mps": [
        -0.0014849394792690873,
        0.0010278368135914207
      ],
      "linear_speed_mps": 0.0023302843598342637,
      "local_corner_max_m": [
        0.05221410392429668,
        0.2024614658670748,
        0.03644372987705663
      ],
      "local_corner_min_m": [
        -0.052629092704266356,
        0.1298122766856783,
        -0.03601230395670668
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07755330974299596,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11378132665987761,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025539761317707868,
      "step_index": 2060,
      "timestamp_seconds": 8.240000391378999,
      "trace_row": 2060,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09769607055357345,
      "vertical_lower_margin_m": 0.10804688137217694,
      "vertical_upper_margin_m": -0.09769607055357345
    },
    {
      "actual_left_finger_qpos_m": [
        0.023373540490865707,
        0.021787699311971664
      ],
      "angular_speed_rps": 0.01832169133177455,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00020333456808946382,
        0.1661323836932136,
        0.0002110448182372493
      ],
      "can_pose": [
        -0.2927338778972626,
        -0.15284474194049835,
        0.9427916407585144,
        0.0021499046124517918,
        0.700425922870636,
        0.047273118048906326,
        0.7121549248695374
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008096135629088194,
      "can_relative_translation_from_partial_start_m": [
        0.0005302727222442627,
        -0.0003235340118408203,
        -0.001177281141281128
      ],
      "can_to_box_relative_orientation_rad": 1.502014961629676,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.004480424802750349,
        0.004480424802750349
      ],
      "left_finger_qf_audit_only": [
        6.812214374542236,
        -6.812229156494141
      ],
      "left_finger_qvel_mps": [
        -0.001750968280248344,
        0.0012877293629571795
      ],
      "linear_speed_mps": 0.002342010823789829,
      "local_corner_max_m": [
        0.05221951356785015,
        0.20245491781206326,
        0.03644089931620598
      ],
      "local_corner_min_m": [
        -0.05262618270402908,
        0.12980984957436392,
        -0.03601880967973148
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07755797788493368,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11378783238290241,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025534351674154396,
      "step_index": 2061,
      "timestamp_seconds": 8.244000391568989,
      "trace_row": 2061,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0976895224985619,
      "vertical_lower_margin_m": 0.10804445426086257,
      "vertical_upper_margin_m": -0.0976895224985619
    },
    {
      "actual_left_finger_qpos_m": [
        0.023369276896119118,
        0.02179284393787384
      ],
      "angular_speed_rps": 0.01621847459160917,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001992386003869806,
        0.16612770085816764,
        0.00020640488015216674
      ],
      "can_pose": [
        -0.29274076223373413,
        -0.15284067392349243,
        0.9427885413169861,
        0.002122130012139678,
        0.7004372477531433,
        0.04727775603532791,
        0.7121434807777405
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008158911728674112,
      "can_relative_translation_from_partial_start_m": [
        0.0005343407392501831,
        -0.0003266334533691406,
        -0.0011841654777526855
      ],
      "can_to_box_relative_orientation_rad": 1.502048918457059,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.004643126390874386,
        0.004643126390874386
      ],
      "left_finger_qf_audit_only": [
        6.812481880187988,
        -6.812500953674316
      ],
      "left_finger_qvel_mps": [
        -0.0018202252686023712,
        0.001320032635703683
      ],
      "linear_speed_mps": 0.002144023405520799,
      "local_corner_max_m": [
        0.05222398513010504,
        0.20244764952977745,
        0.036437431042831425
      ],
      "local_corner_min_m": [
        -0.05262246233087897,
        0.12980775218655782,
        -0.03602462128252709
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07756261782301876,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11379364398569802,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02552988011189951,
      "step_index": 2062,
      "timestamp_seconds": 8.248000391758978,
      "trace_row": 2062,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09768225421627609,
      "vertical_lower_margin_m": 0.10804235687305647,
      "vertical_upper_margin_m": -0.09768225421627609
    },
    {
      "actual_left_finger_qpos_m": [
        0.02336503565311432,
        0.021797994151711464
      ],
      "angular_speed_rps": 0.016455656405798165,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001950276706513543,
        0.16612296719306563,
        0.000202101676563593
      ],
      "can_pose": [
        -0.2927476465702057,
        -0.15283654630184174,
        0.9427849054336548,
        0.0020954033825546503,
        0.700448215007782,
        0.04728853702545166,
        0.7121319770812988
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008224239885377285,
      "can_relative_translation_from_partial_start_m": [
        0.0005384683609008789,
        -0.00033026933670043945,
        -0.0011910498142242432
      ],
      "can_to_box_relative_orientation_rad": 1.5020729499630918,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.004805827978998423,
        0.004805827978998423
      ],
      "left_finger_qf_audit_only": [
        6.812724590301514,
        -6.812742710113525
      ],
      "left_finger_qvel_mps": [
        -0.001798118930310011,
        0.0013415641151368618
      ],
      "linear_speed_mps": 0.0022029949694574802,
      "local_corner_max_m": [
        0.0522290800780868,
        0.20244079474734522,
        0.03643465817894681
      ],
      "local_corner_min_m": [
        -0.05261913541938951,
        0.12980513963878604,
        -0.036030454825819624
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07756692102660734,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11379947752899056,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02552478516391775,
      "step_index": 2063,
      "timestamp_seconds": 8.252000391948968,
      "trace_row": 2063,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09767539943384386,
      "vertical_lower_margin_m": 0.10803974432528468,
      "vertical_upper_margin_m": -0.09767539943384386
    },
    {
      "actual_left_finger_qpos_m": [
        0.023360684514045715,
        0.021803269162774086
      ],
      "angular_speed_rps": 0.016903448553694196,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00019103310498849724,
        0.1661184681516088,
        0.000197899912679822
      ],
      "can_pose": [
        -0.2927546501159668,
        -0.15283265709877014,
        0.942781388759613,
        0.002067799447104335,
        0.7004579901695251,
        0.047301825135946274,
        0.7121215462684631
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008291698792057578,
      "can_relative_translation_from_partial_start_m": [
        0.0005423575639724731,
        -0.0003337860107421875,
        -0.0011980533599853516
      ],
      "can_to_box_relative_orientation_rad": 1.5020948679220025,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.004968529567122459,
        0.004968529567122459
      ],
      "left_finger_qf_audit_only": [
        6.812974452972412,
        -6.812989234924316
      ],
      "left_finger_qvel_mps": [
        -0.0017142965225502849,
        0.0012427672045305371
      ],
      "linear_speed_mps": 0.0021872148786297617,
      "local_corner_max_m": [
        0.052234165882521055,
        0.20243438144382642,
        0.03643231067144975
      ],
      "local_corner_min_m": [
        -0.05261623209249805,
        0.12980255485939118,
        -0.03603651084609011
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757112279049111,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11380553354926104,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02551969935948349,
      "step_index": 2064,
      "timestamp_seconds": 8.256000392138958,
      "trace_row": 2064,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09766898613032506,
      "vertical_lower_margin_m": 0.10803715954588983,
      "vertical_upper_margin_m": -0.09766898613032506
    },
    {
      "actual_left_finger_qpos_m": [
        0.023356322199106216,
        0.021808527410030365
      ],
      "angular_speed_rps": 0.015847018888534427,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00018698225953153735,
        0.16611373127749562,
        0.0001936486661562875
      ],
      "can_pose": [
        -0.29276126623153687,
        -0.1528286635875702,
        0.9427779316902161,
        0.0020413389429450035,
        0.700468897819519,
        0.047309644520282745,
        0.7121104001998901
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008354205655265175,
      "can_relative_translation_from_partial_start_m": [
        0.0005463510751724243,
        -0.00033724308013916016,
        -0.00120466947555542
      ],
      "can_to_box_relative_orientation_rad": 1.5021225738619433,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.005131231155246496,
        0.005131231155246496
      ],
      "left_finger_qf_audit_only": [
        6.813205718994141,
        -6.8132195472717285
      ],
      "left_finger_qvel_mps": [
        -0.0018641551723703742,
        0.0013993596658110619
      ],
      "linear_speed_mps": 0.0021164894127364067,
      "local_corner_max_m": [
        0.05223885535197775,
        0.20242737553948065,
        0.03642938920052141
      ],
      "local_corner_min_m": [
        -0.05261281987104083,
        0.1298000870155106,
        -0.036042091868208836
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757537403701464,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11381111457137977,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025515009890026794,
      "step_index": 2065,
      "timestamp_seconds": 8.260000392328948,
      "trace_row": 2065,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09766198022597929,
      "vertical_lower_margin_m": 0.10803469170200924,
      "vertical_upper_margin_m": -0.09766198022597929
    },
    {
      "actual_left_finger_qpos_m": [
        0.023352045565843582,
        0.021813753992319107
      ],
      "angular_speed_rps": 0.015777619619929333,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001831437266357483,
        0.166109102657232,
        0.00018991417613078987
      ],
      "can_pose": [
        -0.2927675247192383,
        -0.15282490849494934,
        0.9427743554115295,
        0.002015301026403904,
        0.700478732585907,
        0.04732035472989082,
        0.712100088596344
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00841709135177034,
      "can_relative_translation_from_partial_start_m": [
        0.0005501061677932739,
        -0.0003408193588256836,
        -0.001210927963256836
      ],
      "can_to_box_relative_orientation_rad": 1.5021457334218027,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.005293932743370533,
        0.005293932743370533
      ],
      "left_finger_qf_audit_only": [
        6.813445568084717,
        -6.813465595245361
      ],
      "left_finger_qvel_mps": [
        -0.0018318563234061003,
        0.001347268233075738
      ],
      "linear_speed_mps": 0.002031919533783475,
      "local_corner_max_m": [
        0.05224357196632193,
        0.20242077582436535,
        0.03642723354388194
      ],
      "local_corner_min_m": [
        -0.05260985941959345,
        0.12979742949009865,
        -0.03604740519162036
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757910852704014,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1138164278947913,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02551029327568262,
      "step_index": 2066,
      "timestamp_seconds": 8.264000392518938,
      "trace_row": 2066,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09765538051086399,
      "vertical_lower_margin_m": 0.10803203417659729,
      "vertical_upper_margin_m": -0.09765538051086399
    },
    {
      "actual_left_finger_qpos_m": [
        0.0233476459980011,
        0.021818997338414192
      ],
      "angular_speed_rps": 0.015321119091096467,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000179246370185987,
        0.16610458823307717,
        0.00018594694007417756
      ],
      "can_pose": [
        -0.29277390241622925,
        -0.15282107889652252,
        0.9427710175514221,
        0.0019891513511538506,
        0.7004879117012024,
        0.04732929542660713,
        0.7120905518531799
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00847812524750962,
      "can_relative_translation_from_partial_start_m": [
        0.0005539357662200928,
        -0.00034415721893310547,
        -0.0012173056602478027
      ],
      "can_to_box_relative_orientation_rad": 1.5021714951128162,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.00545663433149457,
        0.00545663433149457
      ],
      "left_finger_qf_audit_only": [
        6.813669681549072,
        -6.813687801361084
      ],
      "left_finger_qvel_mps": [
        -0.0018502373713999987,
        0.0013553424505516887
      ],
      "linear_speed_mps": 0.002038414622944347,
      "local_corner_max_m": [
        0.052248201021660445,
        0.202414240741691,
        0.03642479391895115
      ],
      "local_corner_min_m": [
        -0.05260669376203242,
        0.12979493572446332,
        -0.03605290003880279
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758307576309675,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11382192274197372,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0255056642203441,
      "step_index": 2067,
      "timestamp_seconds": 8.268000392708927,
      "trace_row": 2067,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09764884542818965,
      "vertical_lower_margin_m": 0.10802954041096197,
      "vertical_upper_margin_m": -0.09764884542818965
    },
    {
      "actual_left_finger_qpos_m": [
        0.023343244567513466,
        0.021824363619089127
      ],
      "angular_speed_rps": 0.015175074954990857,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00017542712000148675,
        0.16609980841928285,
        0.00018224062815547226
      ],
      "can_pose": [
        -0.29277992248535156,
        -0.15281732380390167,
        0.9427673816680908,
        0.001964040333405137,
        0.7004981637001038,
        0.04733775928616524,
        0.7120798826217651
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008538221946775065,
      "can_relative_translation_from_partial_start_m": [
        0.0005576908588409424,
        -0.0003477931022644043,
        -0.0012233257293701172
      ],
      "can_to_box_relative_orientation_rad": 1.5021963610258209,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.005619335919618607,
        0.005619335919618607
      ],
      "left_finger_qf_audit_only": [
        6.813889980316162,
        -6.813907623291016
      ],
      "left_finger_qvel_mps": [
        -0.0018607787787914276,
        0.0013857384910807014
      ],
      "linear_speed_mps": 0.0019931381410572147,
      "local_corner_max_m": [
        0.052252712729611905,
        0.20240737302757206,
        0.03642242017396413
      ],
      "local_corner_min_m": [
        -0.05260356696961488,
        0.12979224381099363,
        -0.03605793891765319
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758678207501546,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11382696162082412,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02550115251239264,
      "step_index": 2068,
      "timestamp_seconds": 8.272000392898917,
      "trace_row": 2068,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0976419777140707,
      "vertical_lower_margin_m": 0.10802684849749228,
      "vertical_upper_margin_m": -0.0976419777140707
    },
    {
      "actual_left_finger_qpos_m": [
        0.023338835686445236,
        0.02182966284453869
      ],
      "angular_speed_rps": 0.015314337556126361,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00017170582723866068,
        0.16609488443380005,
        0.0001786390694860085
      ],
      "can_pose": [
        -0.29278600215911865,
        -0.15281368792057037,
        0.9427634477615356,
        0.00193877168931067,
        0.7005074620246887,
        0.04734860360622406,
        0.712070107460022
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008599331447722047,
      "can_relative_translation_from_partial_start_m": [
        0.0005613267421722412,
        -0.0003517270088195801,
        -0.001229405403137207
      ],
      "can_to_box_relative_orientation_rad": 1.5022182322664799,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.005782037507742643,
        0.005782037507742643
      ],
      "left_finger_qf_audit_only": [
        6.814102649688721,
        -6.81412410736084
      ],
      "left_finger_qvel_mps": [
        -0.0020647465717047453,
        0.0015519808512181044
      ],
      "linear_speed_mps": 0.0020257359042574743,
      "local_corner_max_m": [
        0.05225732316577386,
        0.20240058665674754,
        0.036420401116720014
      ],
      "local_corner_min_m": [
        -0.05260073482025118,
        0.12978918221085256,
        -0.036063122977748
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759038363368492,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11383214568091893,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025496542076230685,
      "step_index": 2069,
      "timestamp_seconds": 8.276000393088907,
      "trace_row": 2069,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09763519134324618,
      "vertical_lower_margin_m": 0.1080237868973512,
      "vertical_upper_margin_m": -0.09763519134324618
    },
    {
      "actual_left_finger_qpos_m": [
        0.023334385827183723,
        0.021834980696439743
      ],
      "angular_speed_rps": 0.014158687515306578,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00016784242971176755,
        0.16609011697992093,
        0.00017522596896207832
      ],
      "can_pose": [
        -0.2927916347980499,
        -0.15280988812446594,
        0.9427597522735596,
        0.0019147953717038035,
        0.7005161643028259,
        0.047356922179460526,
        0.7120610475540161
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008655711528840619,
      "can_relative_translation_from_partial_start_m": [
        0.0005651265382766724,
        -0.0003554224967956543,
        -0.0012350380420684814
      ],
      "can_to_box_relative_orientation_rad": 1.5022416835471797,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.00594473909586668,
        0.00594473909586668
      ],
      "left_finger_qf_audit_only": [
        6.814302444458008,
        -6.8143229484558105
      ],
      "left_finger_qvel_mps": [
        -0.001977878622710705,
        0.0014875171473249793
      ],
      "linear_speed_mps": 0.001933612187460153,
      "local_corner_max_m": [
        0.052261867224654035,
        0.20239394528182297,
        0.03641837065061754
      ],
      "local_corner_min_m": [
        -0.05259755208407757,
        0.1297862886780189,
        -0.03606791871269338
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759379673420885,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11383694141586431,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025491998017350512,
      "step_index": 2070,
      "timestamp_seconds": 8.280000393278897,
      "trace_row": 2070,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09762854996832161,
      "vertical_lower_margin_m": 0.10802089336451753,
      "vertical_upper_margin_m": -0.09762854996832161
    },
    {
      "actual_left_finger_qpos_m": [
        0.023329906165599823,
        0.02184038609266281
      ],
      "angular_speed_rps": 0.014218638591981015,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00016422495677406723,
        0.166085330680682,
        0.00017191287328638394
      ],
      "can_pose": [
        -0.2927972376346588,
        -0.1528063416481018,
        0.9427559971809387,
        0.0018905544420704246,
        0.7005242705345154,
        0.04736607149243355,
        0.712052583694458
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008712508382166105,
      "can_relative_translation_from_partial_start_m": [
        0.0005686730146408081,
        -0.0003591775894165039,
        -0.0012406408786773682
      ],
      "can_to_box_relative_orientation_rad": 1.5022644046499618,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.006107440683990717,
        0.006107440683990717
      ],
      "left_finger_qf_audit_only": [
        6.8144965171813965,
        -6.81451416015625
      ],
      "left_finger_qvel_mps": [
        -0.0018784652929753065,
        0.0013738664565607905
      ],
      "linear_speed_mps": 0.001905091660230239,
      "local_corner_max_m": [
        0.052266233880962076,
        0.2023873761460745,
        0.03641656450749797
      ],
      "local_corner_min_m": [
        -0.05259468379451021,
        0.12978328521528948,
        -0.036072738760925205
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759710982988455,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11384176146409614,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02548763136104247,
      "step_index": 2071,
      "timestamp_seconds": 8.284000393468887,
      "trace_row": 2071,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09762198083257313,
      "vertical_lower_margin_m": 0.10801788990178812,
      "vertical_upper_margin_m": -0.09762198083257313
    },
    {
      "actual_left_finger_qpos_m": [
        0.023325450718402863,
        0.02184572070837021
      ],
      "angular_speed_rps": 0.014441622845214778,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00016059730303472075,
        0.16608064342098183,
        0.00016870858126566413
      ],
      "can_pose": [
        -0.2928027808666229,
        -0.15280279517173767,
        0.9427522420883179,
        0.0018667205004021525,
        0.7005329728126526,
        0.047376323491334915,
        0.7120433449745178
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008770144740073612,
      "can_relative_translation_from_partial_start_m": [
        0.0005722194910049438,
        -0.0003629326820373535,
        -0.0012461841106414795
      ],
      "can_to_box_relative_orientation_rad": 1.5022850032650086,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.006270142272114754,
        0.006270142272114754
      ],
      "left_finger_qf_audit_only": [
        6.814694881439209,
        -6.814708709716797
      ],
      "left_finger_qvel_mps": [
        -0.0019235117360949516,
        0.0014260951429605484
      ],
      "linear_speed_mps": 0.0018941625845481792,
      "local_corner_max_m": [
        0.05227070212385135,
        0.20238093607487462,
        0.036414856306815846
      ],
      "local_corner_min_m": [
        -0.05259189672992076,
        0.12978035076708905,
        -0.03607743914428452
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07760031412190527,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11384646184745545,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0254831631181532,
      "step_index": 2072,
      "timestamp_seconds": 8.288000393658876,
      "trace_row": 2072,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09761554076137326,
      "vertical_lower_margin_m": 0.10801495545358769,
      "vertical_upper_margin_m": -0.09761554076137326
    },
    {
      "actual_left_finger_qpos_m": [
        0.023320838809013367,
        0.021851254627108574
      ],
      "angular_speed_rps": 0.013610084513435233,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00015691913698701043,
        0.16607571288498024,
        0.000165683191696131
      ],
      "can_pose": [
        -0.2928079664707184,
        -0.15279917418956757,
        0.9427484273910522,
        0.0018427700269967318,
        0.7005402445793152,
        0.047383882105350494,
        0.7120357751846313
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008824374849030658,
      "can_relative_translation_from_partial_start_m": [
        0.0005758404731750488,
        -0.0003667473793029785,
        -0.0012513697147369385
      ],
      "can_to_box_relative_orientation_rad": 1.5023094963080934,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0064328438602387905,
        0.0064328438602387905
      ],
      "left_finger_qf_audit_only": [
        6.814885139465332,
        -6.814903259277344
      ],
      "left_finger_qvel_mps": [
        -0.0019415062852203846,
        0.0014362386427819729
      ],
      "linear_speed_mps": 0.0018465154981254957,
      "local_corner_max_m": [
        0.05227499806356578,
        0.20237422451255527,
        0.03641328499590524
      ],
      "local_corner_min_m": [
        -0.0525888363375398,
        0.12977720125740522,
        -0.036081918612512975
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776033395114748,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1138509413156839,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025478867178438766,
      "step_index": 2073,
      "timestamp_seconds": 8.292000393848866,
      "trace_row": 2073,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0976088291990539,
      "vertical_lower_margin_m": 0.10801180594390386,
      "vertical_upper_margin_m": -0.0976088291990539
    },
    {
      "actual_left_finger_qpos_m": [
        0.023316340520977974,
        0.021856633946299553
      ],
      "angular_speed_rps": 0.013588541506910119,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00015344998417649025,
        0.16607099623170618,
        0.0001626401013910539
      ],
      "can_pose": [
        -0.29281312227249146,
        -0.15279576182365417,
        0.942744791507721,
        0.001819499535486102,
        0.700548529624939,
        0.04739135131239891,
        0.7120272517204285
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008878435786854533,
      "can_relative_translation_from_partial_start_m": [
        0.0005792528390884399,
        -0.00037038326263427734,
        -0.0012565255165100098
      ],
      "can_to_box_relative_orientation_rad": 1.5023330975208837,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.006595545448362827,
        0.006595545448362827
      ],
      "left_finger_qf_audit_only": [
        6.8150739669799805,
        -6.815093040466309
      ],
      "left_finger_qvel_mps": [
        -0.002033099764958024,
        0.0015252858866006136
      ],
      "linear_speed_mps": 0.0017931497386193573,
      "local_corner_max_m": [
        0.052279077381790384,
        0.20236767151439572,
        0.03641156065341772
      ],
      "local_corner_min_m": [
        -0.052585977350143365,
        0.12977432094901664,
        -0.03608628045063561
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07760638260177988,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11385530315380654,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025474787860214163,
      "step_index": 2074,
      "timestamp_seconds": 8.296000394038856,
      "trace_row": 2074,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09760227620089436,
      "vertical_lower_margin_m": 0.10800892563551528,
      "vertical_upper_margin_m": -0.09760227620089436
    },
    {
      "actual_left_finger_qpos_m": [
        0.023311853408813477,
        0.02186201512813568
      ],
      "angular_speed_rps": 0.013957622046348124,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00014992913779973693,
        0.16606605600479019,
        0.00015965204545798084
      ],
      "can_pose": [
        -0.29281845688819885,
        -0.1527923345565796,
        0.9427406191825867,
        0.001796758733689785,
        0.700556218624115,
        0.04740289971232414,
        0.7120189070701599
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008934125133358298,
      "can_relative_translation_from_partial_start_m": [
        0.0005826801061630249,
        -0.0003745555877685547,
        -0.0012618601322174072
      ],
      "can_to_box_relative_orientation_rad": 1.5023503529219353,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.006758247036486864,
        0.006758247036486864
      ],
      "left_finger_qf_audit_only": [
        6.815251350402832,
        -6.815270900726318
      ],
      "left_finger_qvel_mps": [
        -0.002095793839544058,
        0.0015860800631344318
      ],
      "linear_speed_mps": 0.0018975737123259396,
      "local_corner_max_m": [
        0.05228354630820528,
        0.20236122031348824,
        0.036410165521994664
      ],
      "local_corner_min_m": [
        -0.05258340458380473,
        0.12977089169609213,
        -0.0360908614310787
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07760937065771295,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11385988413424963,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025470318933799266,
      "step_index": 2075,
      "timestamp_seconds": 8.300000394228846,
      "trace_row": 2075,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09759582499998688,
      "vertical_lower_margin_m": 0.10800549638259077,
      "vertical_upper_margin_m": -0.09759582499998688
    },
    {
      "actual_left_finger_qpos_m": [
        0.023307254537940025,
        0.021867524832487106
      ],
      "angular_speed_rps": 0.013012984875755345,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001463827300490217,
        0.16606111860193817,
        0.00015684523182712962
      ],
      "can_pose": [
        -0.2928234338760376,
        -0.15278886258602142,
        0.9427365660667419,
        0.0017743941862136126,
        0.7005627155303955,
        0.04741227999329567,
        0.7120120525360107
      ],
      "can_relative_orientation_from_partial_start_rad": 0.008986169032047244,
      "can_relative_translation_from_partial_start_m": [
        0.0005861520767211914,
        -0.00037860870361328125,
        -0.0012668371200561523
      ],
      "can_to_box_relative_orientation_rad": 1.5023700635598158,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.006920948624610901,
        0.006920948624610901
      ],
      "left_finger_qf_audit_only": [
        6.815424919128418,
        -6.815442085266113
      ],
      "left_finger_qvel_mps": [
        -0.0020184561144560575,
        0.001500436570495367
      ],
      "linear_speed_mps": 0.0018243617119390564,
      "local_corner_max_m": [
        0.052287861253267454,
        0.20235478821439679,
        0.036408894579786966
      ],
      "local_corner_min_m": [
        -0.0525806267133655,
        0.12976744898947956,
        -0.036095204116132706
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776121774713438,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11386422681930364,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025466003988737093,
      "step_index": 2076,
      "timestamp_seconds": 8.304000394418836,
      "trace_row": 2076,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09758939290089542,
      "vertical_lower_margin_m": 0.1080020536759782,
      "vertical_upper_margin_m": -0.09758939290089542
    },
    {
      "actual_left_finger_qpos_m": [
        0.023302681744098663,
        0.021873092278838158
      ],
      "angular_speed_rps": 0.012724421235586406,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001431177729880606,
        0.16605620348014116,
        0.00015397975234443528
      ],
      "can_pose": [
        -0.2928282618522644,
        -0.15278564393520355,
        0.9427327513694763,
        0.001752039068378508,
        0.7005699872970581,
        0.047418493777513504,
        0.712004542350769
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009036681693416454,
      "can_relative_translation_from_partial_start_m": [
        0.0005893707275390625,
        -0.00038242340087890625,
        -0.001271665096282959
      ],
      "can_to_box_relative_orientation_rad": 1.5023940676750032,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.007083650212734938,
        0.007083650212734938
      ],
      "left_finger_qf_audit_only": [
        6.815586566925049,
        -6.815605640411377
      ],
      "left_finger_qvel_mps": [
        -0.0021572608966380358,
        0.0016478250036016107
      ],
      "linear_speed_mps": 0.0017360331610746231,
      "local_corner_max_m": [
        0.052291632930069054,
        0.2023481140165061,
        0.0364072892134647
      ],
      "local_corner_min_m": [
        -0.052577868476045175,
        0.12976429294377623,
        -0.03609932970877583
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776150429508265,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11386835241194676,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025462232311935493,
      "step_index": 2077,
      "timestamp_seconds": 8.308000394608825,
      "trace_row": 2077,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09758271870300474,
      "vertical_lower_margin_m": 0.10799889763027487,
      "vertical_upper_margin_m": -0.09758271870300474
    },
    {
      "actual_left_finger_qpos_m": [
        0.023298170417547226,
        0.021878447383642197
      ],
      "angular_speed_rps": 0.01207849641367992,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00013967181074547863,
        0.1660514040345007,
        0.0001516587553045956
      ],
      "can_pose": [
        -0.29283255338668823,
        -0.15278226137161255,
        0.9427288174629211,
        0.0017313103890046477,
        0.7005764842033386,
        0.04742653667926788,
        0.7119976878166199
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009084974389763545,
      "can_relative_translation_from_partial_start_m": [
        0.0005927532911300659,
        -0.00038635730743408203,
        -0.0012759566307067871
      ],
      "can_to_box_relative_orientation_rad": 1.5024132135926767,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0072463518008589745,
        0.0072463518008589745
      ],
      "left_finger_qf_audit_only": [
        6.815742492675781,
        -6.815768241882324
      ],
      "left_finger_qvel_mps": [
        -0.0021528310608118773,
        0.0016079331981018186
      ],
      "linear_speed_mps": 0.0016832747220147388,
      "local_corner_max_m": [
        0.052295737336963244,
        0.202341842335235,
        0.03640630587110205
      ],
      "local_corner_min_m": [
        -0.0525750809584542,
        0.1297609657337664,
        -0.03610298836049286
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07761736394786634,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11387201106366379,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025458127905041303,
      "step_index": 2078,
      "timestamp_seconds": 8.312000394798815,
      "trace_row": 2078,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09757644702173364,
      "vertical_lower_margin_m": 0.10799557042026503,
      "vertical_upper_margin_m": -0.09757644702173364
    },
    {
      "actual_left_finger_qpos_m": [
        0.023293526843190193,
        0.0218840092420578
      ],
      "angular_speed_rps": 0.012020271371756926,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00013639471516896373,
        0.16604631581231277,
        0.0001491646466109664
      ],
      "can_pose": [
        -0.292836993932724,
        -0.15277904272079468,
        0.9427246451377869,
        0.0017103770514950156,
        0.70058274269104,
        0.04743402078747749,
        0.711991012096405
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009132992081842284,
      "can_relative_translation_from_partial_start_m": [
        0.000595971941947937,
        -0.0003905296325683594,
        -0.0012803971767425537
      ],
      "can_to_box_relative_orientation_rad": 1.5024334238797075,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.007409053388983011,
        0.007409053388983011
      ],
      "left_finger_qf_audit_only": [
        6.8158979415893555,
        -6.815919876098633
      ],
      "left_finger_qvel_mps": [
        -0.0021947063505649567,
        0.0016693250508978963
      ],
      "linear_speed_mps": 0.0017227604066275429,
      "local_corner_max_m": [
        0.05229962684165712,
        0.20233525390401796,
        0.03640514313365378
      ],
      "local_corner_min_m": [
        -0.05257241627199505,
        0.12975737772060758,
        -0.03610681384043185
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07761985805655996,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11387583654360278,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025454238400347426,
      "step_index": 2079,
      "timestamp_seconds": 8.316000394988805,
      "trace_row": 2079,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0975698585905166,
      "vertical_lower_margin_m": 0.10799198240710622,
      "vertical_upper_margin_m": -0.0975698585905166
    },
    {
      "actual_left_finger_qpos_m": [
        0.023288853466510773,
        0.021889515221118927
      ],
      "angular_speed_rps": 0.012489607492831676,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001329760746557329,
        0.16604129034696735,
        0.00014702172741243302
      ],
      "can_pose": [
        -0.29284119606018066,
        -0.15277568995952606,
        0.9427205324172974,
        0.0016886135563254356,
        0.7005888819694519,
        0.04744236543774605,
        0.7119844555854797
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009182916471278777,
      "can_relative_translation_from_partial_start_m": [
        0.0005993247032165527,
        -0.00039464235305786133,
        -0.0012845993041992188
      ],
      "can_to_box_relative_orientation_rad": 1.5024536780088227,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.007571754977107048,
        0.007571754977107048
      ],
      "left_finger_qf_audit_only": [
        6.8160400390625,
        -6.816063404083252
      ],
      "left_finger_qvel_mps": [
        -0.0020922974217683077,
        0.0015672207809984684
      ],
      "linear_speed_mps": 0.0016921389710792517,
      "local_corner_max_m": [
        0.05230372863203114,
        0.20232873937843154,
        0.036404454395492336
      ],
      "local_corner_min_m": [
        -0.05256968078134261,
        0.12975384131550316,
        -0.03611041094066747
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776220009757585,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1138794336438384,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025450136609973403,
      "step_index": 2080,
      "timestamp_seconds": 8.320000395178795,
      "trace_row": 2080,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09756334406493018,
      "vertical_lower_margin_m": 0.1079884460020018,
      "vertical_upper_margin_m": -0.09756334406493018
    },
    {
      "actual_left_finger_qpos_m": [
        0.023284131661057472,
        0.0218951553106308
      ],
      "angular_speed_rps": 0.012550401354125221,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00012985801433834654,
        0.166036306937835,
        0.00014496739418612403
      ],
      "can_pose": [
        -0.2928454279899597,
        -0.1527726650238037,
        0.9427161812782288,
        0.0016680245753377676,
        0.7005947828292847,
        0.04745369404554367,
        0.7119778990745544
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009232858901144073,
      "can_relative_translation_from_partial_start_m": [
        0.0006023496389389038,
        -0.00039899349212646484,
        -0.0012888312339782715
      ],
      "can_to_box_relative_orientation_rad": 1.502468139657902,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.007734456565231085,
        0.007734456565231085
      ],
      "left_finger_qf_audit_only": [
        6.816192626953125,
        -6.8162126541137695
      ],
      "left_finger_qvel_mps": [
        -0.002265430521219969,
        0.0017371885478496552
      ],
      "linear_speed_mps": 0.0016954326992784771,
      "local_corner_max_m": [
        0.05230777698251235,
        0.20232253995554994,
        0.036403988706802115
      ],
      "local_corner_min_m": [
        -0.052567493011189015,
        0.12975007392012006,
        -0.03611405391842987
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762405530898481,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1138830766216008,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025446088259492197,
      "step_index": 2081,
      "timestamp_seconds": 8.324000395368785,
      "trace_row": 2081,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09755714464204858,
      "vertical_lower_margin_m": 0.1079846786066187,
      "vertical_upper_margin_m": -0.09755714464204858
    },
    {
      "actual_left_finger_qpos_m": [
        0.02327953279018402,
        0.021900668740272522
      ],
      "angular_speed_rps": 0.01099153224899479,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001266342951882493,
        0.16603134337854375,
        0.00014275802990265651
      ],
      "can_pose": [
        -0.2928493320941925,
        -0.15276947617530823,
        0.9427122473716736,
        0.0016480828635394573,
        0.700600266456604,
        0.047458466142416,
        0.711972177028656
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009276307503070695,
      "can_relative_translation_from_partial_start_m": [
        0.0006055384874343872,
        -0.0004029273986816406,
        -0.0012927353382110596
      ],
      "can_to_box_relative_orientation_rad": 1.5024906310733528,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.007897158153355122,
        0.007897158153355122
      ],
      "left_finger_qf_audit_only": [
        6.816323280334473,
        -6.816348552703857
      ],
      "left_finger_qvel_mps": [
        -0.002344934269785881,
        0.001818011631257832
      ],
      "linear_speed_mps": 0.0015985618827651727,
      "local_corner_max_m": [
        0.05231138901210064,
        0.2023160533716979,
        0.03640293577654835
      ],
      "local_corner_min_m": [
        -0.05256465760247714,
        0.1297466333853896,
        -0.03611741971674304
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762626467326827,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11388644241991397,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025442476229903907,
      "step_index": 2082,
      "timestamp_seconds": 8.328000395558774,
      "trace_row": 2082,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09755065805819653,
      "vertical_lower_margin_m": 0.10798123807188825,
      "vertical_upper_margin_m": -0.09755065805819653
    },
    {
      "actual_left_finger_qpos_m": [
        0.023274896666407585,
        0.021906238049268723
      ],
      "angular_speed_rps": 0.010648982023139164,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00012346171612395707,
        0.16602631084100095,
        0.00014106615373610243
      ],
      "can_pose": [
        -0.2928527295589447,
        -0.15276634693145752,
        0.9427081346511841,
        0.0016288334736600518,
        0.7006052136421204,
        0.04746415093541145,
        0.7119670510292053
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009318626320958643,
      "can_relative_translation_from_partial_start_m": [
        0.0006086677312850952,
        -0.0004070401191711426,
        -0.0012961328029632568
      ],
      "can_to_box_relative_orientation_rad": 1.5025108835608432,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.008059859275817871,
        0.008059859275817871
      ],
      "left_finger_qf_audit_only": [
        6.816455841064453,
        -6.816481113433838
      ],
      "left_finger_qvel_mps": [
        -0.0022397940047085285,
        0.0017081908881664276
      ],
      "linear_speed_mps": 0.0015461524829978725,
      "local_corner_max_m": [
        0.05231502525178802,
        0.20230965284188585,
        0.03640246449302803
      ],
      "local_corner_min_m": [
        -0.052561948684035964,
        0.12974296884011605,
        -0.036120332185555826
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762795654943483,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11388935488872676,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025438839990216525,
      "step_index": 2083,
      "timestamp_seconds": 8.332000395748764,
      "trace_row": 2083,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09754425752838448,
      "vertical_lower_margin_m": 0.10797757352661469,
      "vertical_upper_margin_m": -0.09754425752838448
    },
    {
      "actual_left_finger_qpos_m": [
        0.023270143195986748,
        0.02191188558936119
      ],
      "angular_speed_rps": 0.012200714455421096,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00012030698731316236,
        0.16602126736663292,
        0.000139155334690777
      ],
      "can_pose": [
        -0.29285675287246704,
        -0.1527632772922516,
        0.9427037835121155,
        0.0016082506626844406,
        0.7006105780601501,
        0.04747455194592476,
        0.7119611501693726
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00936724942660879,
      "can_relative_translation_from_partial_start_m": [
        0.0006117373704910278,
        -0.0004113912582397461,
        -0.0013001561164855957
      ],
      "can_to_box_relative_orientation_rad": 1.5025266241911823,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.00822256039828062,
        0.00822256039828062
      ],
      "left_finger_qf_audit_only": [
        6.816586494445801,
        -6.816610813140869
      ],
      "left_finger_qvel_mps": [
        -0.0021898369304835796,
        0.0016594503540545702
      ],
      "linear_speed_mps": 0.0016684975186654568,
      "local_corner_max_m": [
        0.052319033272194976,
        0.20230339241386575,
        0.03640212980688423
      ],
      "local_corner_min_m": [
        -0.05255964724682127,
        0.1297391423194001,
        -0.03612381913750268
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762986736848015,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11389284184067361,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02543483196980957,
      "step_index": 2084,
      "timestamp_seconds": 8.336000395938754,
      "trace_row": 2084,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09753799710036438,
      "vertical_lower_margin_m": 0.10797374700589873,
      "vertical_upper_margin_m": -0.09753799710036438
    },
    {
      "actual_left_finger_qpos_m": [
        0.023265454918146133,
        0.021917466074228287
      ],
      "angular_speed_rps": 0.011096276345709062,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00011721745404572048,
        0.16601616153124932,
        0.00013734577878188325
      ],
      "can_pose": [
        -0.2928604185581207,
        -0.15276025235652924,
        0.9426994323730469,
        0.001589126419275999,
        0.7006159424781799,
        0.04748258739709854,
        0.7119553685188293
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009411620771616596,
      "can_relative_translation_from_partial_start_m": [
        0.0006147623062133789,
        -0.0004157423973083496,
        -0.0013038218021392822
      ],
      "can_to_box_relative_orientation_rad": 1.5025434662789166,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.00838526152074337,
        0.00838526152074337
      ],
      "left_finger_qf_audit_only": [
        6.816707134246826,
        -6.816728591918945
      ],
      "left_finger_qvel_mps": [
        -0.002355275209993124,
        0.0018331867177039385
      ],
      "linear_speed_mps": 0.0016108983263645985,
      "local_corner_max_m": [
        0.052322780926715606,
        0.20229702220451196,
        0.03640164553865949
      ],
      "local_corner_min_m": [
        -0.05255721583480705,
        0.12973530085798668,
        -0.03612695398109572
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763167692438905,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11389597668426665,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02543108431528894,
      "step_index": 2085,
      "timestamp_seconds": 8.340000396128744,
      "trace_row": 2085,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0975316268910106,
      "vertical_lower_margin_m": 0.10796990554448532,
      "vertical_upper_margin_m": -0.0975316268910106
    },
    {
      "actual_left_finger_qpos_m": [
        0.02326071634888649,
        0.02192308008670807
      ],
      "angular_speed_rps": 0.009958264973248622,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00011424403121096383,
        0.16601126916596765,
        0.00013580908588584073
      ],
      "can_pose": [
        -0.29286354780197144,
        -0.15275731682777405,
        0.9426954388618469,
        0.001570830587297678,
        0.7006201148033142,
        0.047487594187259674,
        0.711950957775116
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00945103198718384,
      "can_relative_translation_from_partial_start_m": [
        0.0006176978349685669,
        -0.0004197359085083008,
        -0.0013069510459899902
      ],
      "can_to_box_relative_orientation_rad": 1.50256326708024,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.00854796264320612,
        0.00854796264320612
      ],
      "left_finger_qf_audit_only": [
        6.816831111907959,
        -6.81685733795166
      ],
      "left_finger_qvel_mps": [
        -0.002435905858874321,
        0.0018822720739990473
      ],
      "linear_speed_mps": 0.0014653844331366085,
      "local_corner_max_m": [
        0.05232616241647631,
        0.2022908522188489,
        0.0364012846087044
      ],
      "local_corner_min_m": [
        -0.052554650478898235,
        0.1297316861130864,
        -0.03612966643693272
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763321361728509,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11389868914010365,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02542770282552824,
      "step_index": 2086,
      "timestamp_seconds": 8.344000396318734,
      "trace_row": 2086,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09752545690534754,
      "vertical_lower_margin_m": 0.10796629079958503,
      "vertical_upper_margin_m": -0.09752545690534754
    },
    {
      "actual_left_finger_qpos_m": [
        0.023256050422787666,
        0.021928662434220314
      ],
      "angular_speed_rps": 0.010164484056895566,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00011115380593690327,
        0.16600609288912704,
        0.00013428354848277202
      ],
      "can_pose": [
        -0.29286667704582214,
        -0.1527542620897293,
        0.9426912069320679,
        0.001552131026983261,
        0.7006245255470276,
        0.047492340207099915,
        0.7119463086128235
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009491204121274684,
      "can_relative_translation_from_partial_start_m": [
        0.0006207525730133057,
        -0.0004239678382873535,
        -0.0013100802898406982
      ],
      "can_to_box_relative_orientation_rad": 1.5025840083854076,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.008710663765668869,
        0.008710663765668869
      ],
      "left_finger_qf_audit_only": [
        6.816934585571289,
        -6.816965103149414
      ],
      "left_finger_qvel_mps": [
        -0.002406676299870014,
        0.0018764249980449677
      ],
      "linear_speed_mps": 0.0015213648834203253,
      "local_corner_max_m": [
        0.05232963899667617,
        0.20228433337388796,
        0.03640092335591527
      ],
      "local_corner_min_m": [
        -0.05255194660854995,
        0.12972785240436613,
        -0.03613235625894973
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763473915468816,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11390137896212066,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025424226245328377,
      "step_index": 2087,
      "timestamp_seconds": 8.348000396508723,
      "trace_row": 2087,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0975189380603866,
      "vertical_lower_margin_m": 0.10796245709086477,
      "vertical_upper_margin_m": -0.0975189380603866
    },
    {
      "actual_left_finger_qpos_m": [
        0.023251265287399292,
        0.021934352815151215
      ],
      "angular_speed_rps": 0.010972879945747726,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00010812690443606776,
        0.16600085443142243,
        0.00013293597800384527
      ],
      "can_pose": [
        -0.2928699851036072,
        -0.15275132656097412,
        0.9426864385604858,
        0.0015342604601755738,
        0.7006288170814514,
        0.04750329256057739,
        0.7119414210319519
      ],
      "can_relative_orientation_from_partial_start_rad": 0.00953447905134437,
      "can_relative_translation_from_partial_start_m": [
        0.0006236881017684937,
        -0.00042873620986938477,
        -0.0013133883476257324
      ],
      "can_to_box_relative_orientation_rad": 1.5025950591248571,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.008873364888131618,
        0.008873364888131618
      ],
      "left_finger_qf_audit_only": [
        6.81704044342041,
        -6.817071914672852
      ],
      "left_finger_qvel_mps": [
        -0.0024578063748776913,
        0.0019094673916697502
      ],
      "linear_speed_mps": 0.0016259216407144153,
      "local_corner_max_m": [
        0.05233356548167567,
        0.20227818653248297,
        0.03640109953944137
      ],
      "local_corner_min_m": [
        -0.052549819290547806,
        0.12972352233036188,
        -0.03613522758343368
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763608672516709,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11390425028660461,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025420299760328877,
      "step_index": 2088,
      "timestamp_seconds": 8.352000396698713,
      "trace_row": 2088,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09751279121898161,
      "vertical_lower_margin_m": 0.10795812701686053,
      "vertical_upper_margin_m": -0.09751279121898161
    },
    {
      "actual_left_finger_qpos_m": [
        0.023246433585882187,
        0.021940071135759354
      ],
      "angular_speed_rps": 0.010789447072086393,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00010514912500331208,
        0.16599583428410514,
        0.00013171056313276974
      ],
      "can_pose": [
        -0.2928730845451355,
        -0.15274842083454132,
        0.9426820874214172,
        0.0015155543806031346,
        0.7006329298019409,
        0.04751211032271385,
        0.7119368314743042
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009577396697699407,
      "can_relative_translation_from_partial_start_m": [
        0.0006265938282012939,
        -0.0004330873489379883,
        -0.0013164877891540527
      ],
      "can_to_box_relative_orientation_rad": 1.502610253573702,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.009036066010594368,
        0.009036066010594368
      ],
      "left_finger_qf_audit_only": [
        6.817141532897949,
        -6.817173004150391
      ],
      "left_finger_qvel_mps": [
        -0.0023031837772578,
        0.0017565918387845159
      ],
      "linear_speed_mps": 0.0015203246275664075,
      "local_corner_max_m": [
        0.05233726611758216,
        0.2022720938422934,
        0.03640132905487009
      ],
      "local_corner_min_m": [
        -0.052547564367588784,
        0.1297195747259169,
        -0.03613790792860455
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763731214003816,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11390693063177548,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025416599124422387,
      "step_index": 2089,
      "timestamp_seconds": 8.356000396888703,
      "trace_row": 2089,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09750669852879203,
      "vertical_lower_margin_m": 0.10795417941241553,
      "vertical_upper_margin_m": -0.09750669852879203
    },
    {
      "actual_left_finger_qpos_m": [
        0.023241635411977768,
        0.02194582298398018
      ],
      "angular_speed_rps": 0.009759242396522266,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00010229026159974675,
        0.16599059201573552,
        0.00013030335672625792
      ],
      "can_pose": [
        -0.2928759753704071,
        -0.1527455896139145,
        0.9426777958869934,
        0.0014977360842749476,
        0.7006378173828125,
        0.04751592129468918,
        0.7119318246841431
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009615837213104765,
      "can_relative_translation_from_partial_start_m": [
        0.000629425048828125,
        -0.0004373788833618164,
        -0.0013193786144256592
      ],
      "can_to_box_relative_orientation_rad": 1.5026309791162071,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.009198767133057117,
        0.009198767133057117
      ],
      "left_finger_qf_audit_only": [
        6.817252159118652,
        -6.8172736167907715
      ],
      "left_finger_qvel_mps": [
        -0.0023246670607477427,
        0.001790008507668972
      ],
      "linear_speed_mps": 0.0014745750530828015,
      "local_corner_max_m": [
        0.0523404339095202,
        0.20226546778817467,
        0.036400928793656584
      ],
      "local_corner_min_m": [
        -0.052545014432719694,
        0.12971571624329636,
        -0.03614032208020407
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763871934644467,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.113909344783375,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025413431332484346,
      "step_index": 2090,
      "timestamp_seconds": 8.360000397078693,
      "trace_row": 2090,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09750007247467331,
      "vertical_lower_margin_m": 0.10795032092979501,
      "vertical_upper_margin_m": -0.09750007247467331
    },
    {
      "actual_left_finger_qpos_m": [
        0.023236796259880066,
        0.02195156365633011
      ],
      "angular_speed_rps": 0.010212834818099908,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -9.934568821251544e-05,
        0.16598565998660186,
        0.0001290799147187216
      ],
      "can_pose": [
        -0.29287898540496826,
        -0.15274271368980408,
        0.9426735043525696,
        0.0014798510819673538,
        0.7006412148475647,
        0.047524306923151016,
        0.7119278907775879
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009656314720798259,
      "can_relative_translation_from_partial_start_m": [
        0.0006323009729385376,
        -0.00044167041778564453,
        -0.0013223886489868164
      ],
      "can_to_box_relative_orientation_rad": 1.5026455777281529,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.009361468255519867,
        0.009361468255519867
      ],
      "left_finger_qf_audit_only": [
        6.817349910736084,
        -6.8173723220825195
      ],
      "left_finger_qvel_mps": [
        -0.0023646261543035507,
        0.0018233441514894366
      ],
      "linear_speed_mps": 0.0014947514815009547,
      "local_corner_max_m": [
        0.05234406605620898,
        0.20225955468659296,
        0.0364011357811469
      ],
      "local_corner_min_m": [
        -0.05254275743263398,
        0.12971176528661077,
        -0.036142975951709455
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763994278845221,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11391199865488039,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02540979918579557,
      "step_index": 2091,
      "timestamp_seconds": 8.364000397268683,
      "trace_row": 2091,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0974941593730916,
      "vertical_lower_margin_m": 0.10794636997310941,
      "vertical_upper_margin_m": -0.0974941593730916
    },
    {
      "actual_left_finger_qpos_m": [
        0.023231925442814827,
        0.021957263350486755
      ],
      "angular_speed_rps": 0.010144521187035554,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -9.657644628305317e-05,
        0.16598045592313715,
        0.00012783777938768504
      ],
      "can_pose": [
        -0.29288193583488464,
        -0.1527400016784668,
        0.9426690340042114,
        0.00146191637031734,
        0.7006454467773438,
        0.04753141105175018,
        0.7119232416152954
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009696783172250903,
      "can_relative_translation_from_partial_start_m": [
        0.0006350129842758179,
        -0.00044614076614379883,
        -0.0013253390789031982
      ],
      "can_to_box_relative_orientation_rad": 1.5026619836391817,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.009524169377982616,
        0.009524169377982616
      ],
      "left_finger_qf_audit_only": [
        6.817447662353516,
        -6.817469596862793
      ],
      "left_finger_qvel_mps": [
        -0.0024109934456646442,
        0.00183557765558362
      ],
      "linear_speed_mps": 0.001500917494490226,
      "local_corner_max_m": [
        0.05234741665919454,
        0.2022532127433354,
        0.03640117422784406
      ],
      "local_corner_min_m": [
        -0.052540569551760674,
        0.1297076991029389,
        -0.03614549866906869
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764118492378325,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11391452137223962,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025406448582810007,
      "step_index": 2092,
      "timestamp_seconds": 8.368000397458673,
      "trace_row": 2092,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09748781742983405,
      "vertical_lower_margin_m": 0.10794230378943753,
      "vertical_upper_margin_m": -0.09748781742983405
    },
    {
      "actual_left_finger_qpos_m": [
        0.023227136582136154,
        0.021963011473417282
      ],
      "angular_speed_rps": 0.009124172607540589,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -9.388026703557872e-05,
        0.16597534479171527,
        0.00012691838520900722
      ],
      "can_pose": [
        -0.29288437962532043,
        -0.1527373492717743,
        0.9426646828651428,
        0.001445074682123959,
        0.7006483674049377,
        0.04753696545958519,
        0.7119200825691223
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009732782025432892,
      "can_relative_translation_from_partial_start_m": [
        0.0006376653909683228,
        -0.00045049190521240234,
        -0.0013277828693389893
      ],
      "can_to_box_relative_orientation_rad": 1.5026789472254338,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.009686870500445366,
        0.009686870500445366
      ],
      "left_finger_qf_audit_only": [
        6.817536354064941,
        -6.817562580108643
      ],
      "left_finger_qvel_mps": [
        -0.0024948366917669773,
        0.0019419047748669982
      ],
      "linear_speed_mps": 0.0014128822738625406,
      "local_corner_max_m": [
        0.0523505662802603,
        0.2022470708004036,
        0.036401478433899015
      ],
      "local_corner_min_m": [
        -0.05253832681433146,
        0.12970361878302694,
        -0.036147641663481
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764210431796192,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11391666436665193,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025403298961744245,
      "step_index": 2093,
      "timestamp_seconds": 8.372000397648662,
      "trace_row": 2093,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09748167548690224,
      "vertical_lower_margin_m": 0.10793822346952558,
      "vertical_upper_margin_m": -0.09748167548690224
    },
    {
      "actual_left_finger_qpos_m": [
        0.023222308605909348,
        0.021968724206089973
      ],
      "angular_speed_rps": 0.009689399267817929,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -9.102244968328677e-05,
        0.16597022967477304,
        0.00012611354918551365
      ],
      "can_pose": [
        -0.292886883020401,
        -0.15273456275463104,
        0.9426600933074951,
        0.0014287299709394574,
        0.7006522417068481,
        0.04754556342959404,
        0.7119156718254089
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009771291861597451,
      "can_relative_translation_from_partial_start_m": [
        0.0006404519081115723,
        -0.0004550814628601074,
        -0.0013302862644195557
      ],
      "can_to_box_relative_orientation_rad": 1.5026909953641823,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.009849571622908115,
        0.009849571622908115
      ],
      "left_finger_qf_audit_only": [
        6.817619323730469,
        -6.817646026611328
      ],
      "left_finger_qvel_mps": [
        -0.0024457713589072227,
        0.0018849060870707035
      ],
      "linear_speed_mps": 0.001481040613612666,
      "local_corner_max_m": [
        0.052354129439557334,
        0.20224104183949865,
        0.03640197586026672
      ],
      "local_corner_min_m": [
        -0.05253617433892388,
        0.12969941751004743,
        -0.036149748761895695
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764290915398542,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11391877146506663,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025399735802447213,
      "step_index": 2094,
      "timestamp_seconds": 8.376000397838652,
      "trace_row": 2094,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09747564652599729,
      "vertical_lower_margin_m": 0.10793402219654608,
      "vertical_upper_margin_m": -0.09747564652599729
    },
    {
      "actual_left_finger_qpos_m": [
        0.02321743033826351,
        0.021974457427859306
      ],
      "angular_speed_rps": 0.008886100450517145,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -8.825614017859973e-05,
        0.16596514872609924,
        0.0001252451681460487
      ],
      "can_pose": [
        -0.29288923740386963,
        -0.15273183584213257,
        0.9426558017730713,
        0.0014118746621534228,
        0.7006539106369019,
        0.04755061864852905,
        0.7119138240814209
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009805601432986501,
      "can_relative_translation_from_partial_start_m": [
        0.0006431788206100464,
        -0.00045937299728393555,
        -0.0013326406478881836
      ],
      "can_to_box_relative_orientation_rad": 1.5027086942163481,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.010012272745370865,
        0.010012272745370865
      ],
      "left_finger_qf_audit_only": [
        6.817711353302002,
        -6.817734718322754
      ],
      "left_finger_qvel_mps": [
        -0.0024268771521747112,
        0.0018597906455397606
      ],
      "linear_speed_mps": 0.0014008131125368539,
      "local_corner_max_m": [
        0.05235730786793932,
        0.20223501991755644,
        0.036402407821095994
      ],
      "local_corner_min_m": [
        -0.05253382014829655,
        0.12969527753464205,
        -0.0361519174848039
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764377753502488,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392094018797483,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025396557374065223,
      "step_index": 2095,
      "timestamp_seconds": 8.380000398028642,
      "trace_row": 2095,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09746962460405507,
      "vertical_lower_margin_m": 0.1079298822211407,
      "vertical_upper_margin_m": -0.09746962460405507
    },
    {
      "actual_left_finger_qpos_m": [
        0.023212561383843422,
        0.02198026515543461
      ],
      "angular_speed_rps": 0.008765895581091847,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -8.564033325775267e-05,
        0.16595998092480657,
        0.00012449575467238239
      ],
      "can_pose": [
        -0.29289141297340393,
        -0.15272925794124603,
        0.9426513910293579,
        0.001395830768160522,
        0.7006574273109436,
        0.04755546525120735,
        0.7119100689888
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009840369267050071,
      "can_relative_translation_from_partial_start_m": [
        0.000645756721496582,
        -0.00046378374099731445,
        -0.0013348162174224854
      ],
      "can_to_box_relative_orientation_rad": 1.5027254436555875,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.010174973867833614,
        0.010174973867833614
      ],
      "left_finger_qf_audit_only": [
        6.817787170410156,
        -6.817813873291016
      ],
      "left_finger_qvel_mps": [
        -0.0024464894086122513,
        0.001896036439575255
      ],
      "linear_speed_mps": 0.0013881942622406373,
      "local_corner_max_m": [
        0.05236031876732389,
        0.20222877212734824,
        0.03640273053871329
      ],
      "local_corner_min_m": [
        -0.05253159943383939,
        0.1296911897222649,
        -0.036153739029368526
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764452694849855,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392276173253946,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02539354647468066,
      "step_index": 2096,
      "timestamp_seconds": 8.384000398218632,
      "trace_row": 2096,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09746337681384688,
      "vertical_lower_margin_m": 0.10792579440876354,
      "vertical_upper_margin_m": -0.09746337681384688
    },
    {
      "actual_left_finger_qpos_m": [
        0.023207683116197586,
        0.021986041218042374
      ],
      "angular_speed_rps": 0.009599129031862138,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -8.304434282815909e-05,
        0.1659548016441107,
        0.00012381736456157366
      ],
      "can_pose": [
        -0.29289382696151733,
        -0.15272673964500427,
        0.9426466822624207,
        0.0013795304112136364,
        0.7006600499153137,
        0.047564759850502014,
        0.7119069695472717
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009877949776929986,
      "can_relative_translation_from_partial_start_m": [
        0.0006482750177383423,
        -0.0004684925079345703,
        -0.0013372302055358887
      ],
      "can_to_box_relative_orientation_rad": 1.502736513002001,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.010337674990296364,
        0.010337674990296364
      ],
      "left_finger_qf_audit_only": [
        6.817863941192627,
        -6.817884922027588
      ],
      "left_finger_qvel_mps": [
        -0.002637072466313839,
        0.00206623412668705
      ],
      "linear_speed_mps": 0.001465043458827026,
      "local_corner_max_m": [
        0.052363677387542995,
        0.20222284683879532,
        0.03640350787026003
      ],
      "local_corner_min_m": [
        -0.05252976607319931,
        0.12968675644942607,
        -0.036155873141136885
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764520533860936,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392489584430782,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02539018785446155,
      "step_index": 2097,
      "timestamp_seconds": 8.388000398408622,
      "trace_row": 2097,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09745745152529396,
      "vertical_lower_margin_m": 0.10792136113592471,
      "vertical_upper_margin_m": -0.09745745152529396
    },
    {
      "actual_left_finger_qpos_m": [
        0.023202840238809586,
        0.021991806104779243
      ],
      "angular_speed_rps": 0.008612394250812148,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -8.037832692528446e-05,
        0.16594965450163746,
        0.00012325712105465403
      ],
      "can_pose": [
        -0.2928959131240845,
        -0.15272413194179535,
        0.942642092704773,
        0.0013641066616401076,
        0.7006618976593018,
        0.04757184907793999,
        0.7119047045707703
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009911603337186008,
      "can_relative_translation_from_partial_start_m": [
        0.0006508827209472656,
        -0.0004730820655822754,
        -0.0013393163681030273
      ],
      "can_to_box_relative_orientation_rad": 1.5027493296898922,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.010500376112759113,
        0.010500376112759113
      ],
      "left_finger_qf_audit_only": [
        6.817931652069092,
        -6.817963123321533
      ],
      "left_finger_qvel_mps": [
        -0.002489781938493252,
        0.001920715905725956
      ],
      "linear_speed_mps": 0.0014189834967237658,
      "local_corner_max_m": [
        0.0523669242434745,
        0.20221694970107307,
        0.03640426571780181
      ],
      "local_corner_min_m": [
        -0.05252768089732507,
        0.12968235930220184,
        -0.0361577514756925
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764576558211628,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392677417886343,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025386940998530047,
      "step_index": 2098,
      "timestamp_seconds": 8.392000398598611,
      "trace_row": 2098,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0974515543875717,
      "vertical_lower_margin_m": 0.10791696398870049,
      "vertical_upper_margin_m": -0.0974515543875717
    },
    {
      "actual_left_finger_qpos_m": [
        0.023197917267680168,
        0.021997623145580292
      ],
      "angular_speed_rps": 0.008633240653535058,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -7.77371694183071e-05,
        0.16594440116822695,
        0.0001226424489687017
      ],
      "can_pose": [
        -0.29289790987968445,
        -0.15272152423858643,
        0.9426376223564148,
        0.0013482020003721118,
        0.7006654143333435,
        0.0475761741399765,
        0.7119009494781494
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009945763028511578,
      "can_relative_translation_from_partial_start_m": [
        0.000653490424156189,
        -0.0004775524139404297,
        -0.001341313123703003
      ],
      "can_to_box_relative_orientation_rad": 1.5027665880728627,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.010663077235221863,
        0.010663077235221863
      ],
      "left_finger_qf_audit_only": [
        6.817995071411133,
        -6.818018436431885
      ],
      "left_finger_qvel_mps": [
        -0.002533313352614641,
        0.0019762625452131033
      ],
      "linear_speed_mps": 0.0013867939751458285,
      "local_corner_max_m": [
        0.05236991738119706,
        0.20221059294628352,
        0.0364046786895067
      ],
      "local_corner_min_m": [
        -0.052525391720033676,
        0.12967820939017038,
        -0.036159393791569294
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764638025420223,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392841649474023,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025383947860807485,
      "step_index": 2099,
      "timestamp_seconds": 8.396000398788601,
      "trace_row": 2099,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09744519763278216,
      "vertical_lower_margin_m": 0.10791281407666903,
      "vertical_upper_margin_m": -0.09744519763278216
    },
    {
      "actual_left_finger_qpos_m": [
        0.023192986845970154,
        0.022003449499607086
      ],
      "angular_speed_rps": 0.008554884924416868,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -7.532481072189401e-05,
        0.16593943650566245,
        0.00012236921252417599
      ],
      "can_pose": [
        -0.2928996980190277,
        -0.1527191698551178,
        0.9426332116127014,
        0.001332889893092215,
        0.7006672620773315,
        0.04758320748806,
        0.7118986248970032
      ],
      "can_relative_orientation_from_partial_start_rad": 0.009979224689293078,
      "can_relative_translation_from_partial_start_m": [
        0.0006558448076248169,
        -0.0004819631576538086,
        -0.0013431012630462646
      ],
      "can_to_box_relative_orientation_rad": 1.5027793152239295,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.010825778357684612,
        0.010825778357684612
      ],
      "left_finger_qf_audit_only": [
        6.818065166473389,
        -6.81809663772583
      ],
      "left_finger_qvel_mps": [
        -0.0025419096928089857,
        0.0019487212412059307
      ],
      "linear_speed_mps": 0.0013274793137507386,
      "local_corner_max_m": [
        0.05237290607536055,
        0.20220487932919384,
        0.036405709922066654
      ],
      "local_corner_min_m": [
        -0.052523555696804336,
        0.12967399368213106,
        -0.0361609714970183
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764665349064676,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392999420018923,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025380959166644,
      "step_index": 2100,
      "timestamp_seconds": 8.400000398978591,
      "trace_row": 2100,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09743948401569248,
      "vertical_lower_margin_m": 0.1079085983686297,
      "vertical_upper_margin_m": -0.09743948401569248
    },
    {
      "actual_left_finger_qpos_m": [
        0.023188089951872826,
        0.022009238600730896
      ],
      "angular_speed_rps": 0.007875858735400988,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -7.270533686448699e-05,
        0.165934022996294,
        0.00012189447751403959
      ],
      "can_pose": [
        -0.2929014265537262,
        -0.15271657705307007,
        0.9426285624504089,
        0.0013180241221562028,
        0.7006699442863464,
        0.04758673161268234,
        0.7118958830833435
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010010060472967255,
      "can_relative_translation_from_partial_start_m": [
        0.0006584376096725464,
        -0.00048661231994628906,
        -0.001344829797744751
      ],
      "can_to_box_relative_orientation_rad": 1.5027961779949983,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.010988479480147362,
        0.010988479480147362
      ],
      "left_finger_qf_audit_only": [
        6.818123817443848,
        -6.818149566650391
      ],
      "left_finger_qvel_mps": [
        -0.0026092263869941235,
        0.0020420700311660767
      ],
      "linear_speed_mps": 0.0013992221434754597,
      "local_corner_max_m": [
        0.05237581130413019,
        0.20219846714276435,
        0.03640621904891711
      ],
      "local_corner_min_m": [
        -0.052521221977859134,
        0.12966957884982366,
        -0.03616243009388903
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764712822565689,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393145279705996,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02537805393787436,
      "step_index": 2101,
      "timestamp_seconds": 8.40400039916858,
      "trace_row": 2101,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09743307182926299,
      "vertical_lower_margin_m": 0.1079041835363223,
      "vertical_upper_margin_m": -0.09743307182926299
    },
    {
      "actual_left_finger_qpos_m": [
        0.0231831856071949,
        0.022015077993273735
      ],
      "angular_speed_rps": 0.007972645082845188,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -7.018686147219899e-05,
        0.16592893797253205,
        0.00012168963125452903
      ],
      "can_pose": [
        -0.29290300607681274,
        -0.1527141034603119,
        0.9426240921020508,
        0.0013032975839450955,
        0.7006716132164001,
        0.047592274844646454,
        0.7118939161300659
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010041173579296557,
      "can_relative_translation_from_partial_start_m": [
        0.0006609112024307251,
        -0.0004910826683044434,
        -0.0013464093208312988
      ],
      "can_to_box_relative_orientation_rad": 1.50281009584627,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.011151180602610111,
        0.011151180602610111
      ],
      "left_finger_qf_audit_only": [
        6.818181991577148,
        -6.8182148933410645
      ],
      "left_finger_qvel_mps": [
        -0.0026399297639727592,
        0.0020520701073110104
      ],
      "linear_speed_mps": 0.0013369173039328567,
      "local_corner_max_m": [
        0.052378782831009385,
        0.20219260347987222,
        0.036407202127696436
      ],
      "local_corner_min_m": [
        -0.05251915655395378,
        0.12966527246519188,
        -0.03616382286518738
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776473330719164,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393284556835831,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02537508241099516,
      "step_index": 2102,
      "timestamp_seconds": 8.40800039935857,
      "trace_row": 2102,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09742720816637086,
      "vertical_lower_margin_m": 0.10789987715169053,
      "vertical_upper_margin_m": -0.09742720816637086
    },
    {
      "actual_left_finger_qpos_m": [
        0.0231782253831625,
        0.022020868957042694
      ],
      "angular_speed_rps": 0.008758905650314213,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -6.773094352852116e-05,
        0.1659237966525643,
        0.00012156444789573895
      ],
      "can_pose": [
        -0.2929047644138336,
        -0.15271173417568207,
        0.9426192045211792,
        0.0012893046950921416,
        0.7006731629371643,
        0.04760243743658066,
        0.7118915915489197
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010074481828519662,
      "can_relative_translation_from_partial_start_m": [
        0.0006632804870605469,
        -0.0004959702491760254,
        -0.0013481676578521729
      ],
      "can_to_box_relative_orientation_rad": 1.5028166202458904,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01131388172507286,
        0.01131388172507286
      ],
      "left_finger_qf_audit_only": [
        6.818238258361816,
        -6.818270683288574
      ],
      "left_finger_qvel_mps": [
        -0.00266575301066041,
        0.0020655810367316008
      ],
      "linear_speed_mps": 0.0014272723639889298,
      "local_corner_max_m": [
        0.052382074341194795,
        0.2021870076257415,
        0.03640851884763019
      ],
      "local_corner_min_m": [
        -0.05251753622825184,
        0.1296605856793871,
        -0.03616538995183871
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764745825527519,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393441265500964,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02537179090080975,
      "step_index": 2103,
      "timestamp_seconds": 8.41200039954856,
      "trace_row": 2103,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09742161231224013,
      "vertical_lower_margin_m": 0.10789519036588574,
      "vertical_upper_margin_m": -0.09742161231224013
    },
    {
      "actual_left_finger_qpos_m": [
        0.023173268884420395,
        0.02202676050364971
      ],
      "angular_speed_rps": 0.007481059542762099,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -6.525458903378079e-05,
        0.1659186495834687,
        0.00012153111091484092
      ],
      "can_pose": [
        -0.2929060459136963,
        -0.15270929038524628,
        0.942614734172821,
        0.00127502775285393,
        0.700674295425415,
        0.047606583684682846,
        0.7118903398513794
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01010317270684496,
      "can_relative_translation_from_partial_start_m": [
        0.0006657242774963379,
        -0.0005004405975341797,
        -0.0013494491577148438
      ],
      "can_to_box_relative_orientation_rad": 1.50283180913836,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01147658284753561,
        0.01147658284753561
      ],
      "left_finger_qf_audit_only": [
        6.818284034729004,
        -6.81831169128418
      ],
      "left_finger_qvel_mps": [
        -0.0026298174634575844,
        0.0020514116622507572
      ],
      "linear_speed_mps": 0.0013133536608059416,
      "local_corner_max_m": [
        0.05238488813650327,
        0.2021810832697013,
        0.0364096027677539
      ],
      "local_corner_min_m": [
        -0.05251539731457083,
        0.12965621589723608,
        -0.03616654054592422
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764749159225609,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393556324909515,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025368977105501275,
      "step_index": 2104,
      "timestamp_seconds": 8.41600039973855,
      "trace_row": 2104,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09741568795619994,
      "vertical_lower_margin_m": 0.10789082058373473,
      "vertical_upper_margin_m": -0.09741568795619994
    },
    {
      "actual_left_finger_qpos_m": [
        0.02316831424832344,
        0.022032661363482475
      ],
      "angular_speed_rps": 0.007349831309927119,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -6.275574934794248e-05,
        0.165913280915164,
        0.00012151877138294465
      ],
      "can_pose": [
        -0.2929072380065918,
        -0.1527068167924881,
        0.9426100850105286,
        0.0012610049452632666,
        0.7006762623786926,
        0.04760989546775818,
        0.7118881940841675
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010131739674245304,
      "can_relative_translation_from_partial_start_m": [
        0.0006681978702545166,
        -0.0005050897598266602,
        -0.0013506412506103516
      ],
      "can_to_box_relative_orientation_rad": 1.5028477405418161,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01163928396999836,
        0.01163928396999836
      ],
      "left_finger_qf_audit_only": [
        6.818333625793457,
        -6.818362712860107
      ],
      "left_finger_qvel_mps": [
        -0.0025908101815730333,
        0.0020115531515330076
      ],
      "linear_speed_mps": 0.0013498716109581505,
      "local_corner_max_m": [
        0.052387655731145205,
        0.2021748198176352,
        0.036410560796685254
      ],
      "local_corner_min_m": [
        -0.05251316722984112,
        0.1296517420126928,
        -0.036167523253919365
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764750393178799,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139365459570903,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02536620951085934,
      "step_index": 2105,
      "timestamp_seconds": 8.42000039992854,
      "trace_row": 2105,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09740942450413383,
      "vertical_lower_margin_m": 0.10788634669919145,
      "vertical_upper_margin_m": -0.09740942450413383
    },
    {
      "actual_left_finger_qpos_m": [
        0.02316330000758171,
        0.02203858084976673
      ],
      "angular_speed_rps": 0.008096922037785252,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -6.0459882903846074e-05,
        0.16590821841818737,
        0.00012152280067412313
      ],
      "can_pose": [
        -0.2929086983203888,
        -0.15270458161830902,
        0.9426054954528809,
        0.0012465852778404951,
        0.7006767988204956,
        0.047617167234420776,
        0.7118871212005615
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010162533720305627,
      "can_relative_translation_from_partial_start_m": [
        0.0006704330444335938,
        -0.0005096793174743652,
        -0.0013521015644073486
      ],
      "can_to_box_relative_orientation_rad": 1.50285886875202,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01180198509246111,
        0.01180198509246111
      ],
      "left_finger_qf_audit_only": [
        6.818382740020752,
        -6.818410873413086
      ],
      "left_finger_qvel_mps": [
        -0.0025557219050824642,
        0.0019609439186751842
      ],
      "linear_speed_mps": 0.0013274165868325807,
      "local_corner_max_m": [
        0.052390547897634865,
        0.2021692028426203,
        0.036411936280120294
      ],
      "local_corner_min_m": [
        -0.05251146766344256,
        0.12964723399375444,
        -0.03616889067877205
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764749990249681,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393791338194298,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025363317344369682,
      "step_index": 2106,
      "timestamp_seconds": 8.42400040011853,
      "trace_row": 2106,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09740380752911894,
      "vertical_lower_margin_m": 0.10788183868025308,
      "vertical_upper_margin_m": -0.09740380752911894
    },
    {
      "actual_left_finger_qpos_m": [
        0.02315831370651722,
        0.02204441837966442
      ],
      "angular_speed_rps": 0.007692457441023388,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -5.8088836846492686e-05,
        0.16590298594332387,
        0.00012161103499275239
      ],
      "can_pose": [
        -0.29291000962257385,
        -0.15270227193832397,
        0.942600667476654,
        0.0012331963516771793,
        0.7006779909133911,
        0.04762447625398636,
        0.7118855118751526
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010192213493592821,
      "can_relative_translation_from_partial_start_m": [
        0.0006727427244186401,
        -0.0005145072937011719,
        -0.0013534128665924072
      ],
      "can_to_box_relative_orientation_rad": 1.5028684308975555,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.011964686214923859,
        0.011964686214923859
      ],
      "left_finger_qf_audit_only": [
        6.818419933319092,
        -6.818444728851318
      ],
      "left_finger_qvel_mps": [
        -0.002626916393637657,
        0.0020341207273304462
      ],
      "linear_speed_mps": 0.0013775768267164105,
      "local_corner_max_m": [
        0.05239351824446134,
        0.20216342773144214,
        0.03641327923451815
      ],
      "local_corner_min_m": [
        -0.05250969591815435,
        0.1296425441552056,
        -0.03617005716453264
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764741166817818,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393907986770357,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025360346997543207,
      "step_index": 2107,
      "timestamp_seconds": 8.42800040030852,
      "trace_row": 2107,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09739803241794077,
      "vertical_lower_margin_m": 0.10787714884170424,
      "vertical_upper_margin_m": -0.09739803241794077
    },
    {
      "actual_left_finger_qpos_m": [
        0.02315339259803295,
        0.022050272673368454
      ],
      "angular_speed_rps": 0.006426156531416286,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -5.5855488261924435e-05,
        0.1658976997026569,
        0.00012187217269782336
      ],
      "can_pose": [
        -0.2929108142852783,
        -0.15270006656646729,
        0.9425959587097168,
        0.0012210451532155275,
        0.7006794810295105,
        0.0476280152797699,
        0.7118838429450989
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010217247581135338,
      "can_relative_translation_from_partial_start_m": [
        0.0006749480962753296,
        -0.0005192160606384277,
        -0.001354217529296875
      ],
      "can_to_box_relative_orientation_rad": 1.5028813285310605,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.012127387337386608,
        0.012127387337386608
      ],
      "left_finger_qf_audit_only": [
        6.818464279174805,
        -6.818493366241455
      ],
      "left_finger_qvel_mps": [
        -0.0027113601099699736,
        0.0021126004867255688
      ],
      "linear_speed_mps": 0.0013153808985857801,
      "local_corner_max_m": [
        0.05239603966390541,
        0.2021574270070876,
        0.03641444362451296
      ],
      "local_corner_min_m": [
        -0.05250775064042923,
        0.12963797239822616,
        -0.03617069927911731
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764715053047311,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393972198228824,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02535782557809914,
      "step_index": 2108,
      "timestamp_seconds": 8.43200040049851,
      "trace_row": 2108,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09739203169358625,
      "vertical_lower_margin_m": 0.10787257708472481,
      "vertical_upper_margin_m": -0.09739203169358625
    },
    {
      "actual_left_finger_qpos_m": [
        0.023148367181420326,
        0.02205619215965271
      ],
      "angular_speed_rps": 0.007046872242590584,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -5.347932971611069e-05,
        0.16589262489736367,
        0.00012219509327349165
      ],
      "can_pose": [
        -0.2929116189479828,
        -0.15269771218299866,
        0.9425916075706482,
        0.001207300228998065,
        0.7006801962852478,
        0.0476309135556221,
        0.7118829488754272
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01024375780244898,
      "can_relative_translation_from_partial_start_m": [
        0.0006773024797439575,
        -0.0005235671997070312,
        -0.0013550221920013428
      ],
      "can_to_box_relative_orientation_rad": 1.502897448566228,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.012290088459849358,
        0.012290088459849358
      ],
      "left_finger_qf_audit_only": [
        6.818497657775879,
        -6.818530559539795
      ],
      "left_finger_qvel_mps": [
        -0.0026509566232562065,
        0.002069136593490839
      ],
      "linear_speed_mps": 0.0012530715360934,
      "local_corner_max_m": [
        0.052398650518875045,
        0.20215156876701545,
        0.03641579784860738
      ],
      "local_corner_min_m": [
        -0.052505609178307266,
        0.1296336810277119,
        -0.036171407662060395
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764682760989744,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394043036523133,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0253552147231295,
      "step_index": 2109,
      "timestamp_seconds": 8.4360004006885,
      "trace_row": 2109,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0973861734535141,
      "vertical_lower_margin_m": 0.10786828571421053,
      "vertical_upper_margin_m": -0.0973861734535141
    },
    {
      "actual_left_finger_qpos_m": [
        0.023143423721194267,
        0.022062106058001518
      ],
      "angular_speed_rps": 0.007345739391724178,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -5.115835562308213e-05,
        0.1658873182498657,
        0.0001225413483383342
      ],
      "can_pose": [
        -0.2929126024246216,
        -0.1526954472064972,
        0.9425867199897766,
        0.001194303622469306,
        0.7006810307502747,
        0.04763759672641754,
        0.711881697177887
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01027195799169583,
      "can_relative_translation_from_partial_start_m": [
        0.0006795674562454224,
        -0.0005284547805786133,
        -0.0013560056686401367
      ],
      "can_to_box_relative_orientation_rad": 1.5029072997003894,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.012452789582312107,
        0.012452789582312107
      ],
      "left_finger_qf_audit_only": [
        6.818532943725586,
        -6.818564414978027
      ],
      "left_finger_qvel_mps": [
        -0.0026751533150672913,
        0.0020859672222286463
      ],
      "linear_speed_mps": 0.0013689820300819963,
      "local_corner_max_m": [
        0.05240151922659436,
        0.20214573996930296,
        0.03641736136263091
      ],
      "local_corner_min_m": [
        -0.052503835937840526,
        0.12962889653042842,
        -0.03617227866595424
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776464813548326,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394130136912517,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025352346015410185,
      "step_index": 2110,
      "timestamp_seconds": 8.440000400878489,
      "trace_row": 2110,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0973803446558016,
      "vertical_lower_margin_m": 0.10786350121692706,
      "vertical_upper_margin_m": -0.0973803446558016
    },
    {
      "actual_left_finger_qpos_m": [
        0.023138318210840225,
        0.022067993879318237
      ],
      "angular_speed_rps": 0.0073968204994570306,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -4.8962588630824255e-05,
        0.16588211694249522,
        0.00012287327582527485
      ],
      "can_pose": [
        -0.2929135859012604,
        -0.15269330143928528,
        0.9425820112228394,
        0.0011807973496615887,
        0.7006807923316956,
        0.04764362797141075,
        0.7118816375732422
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01029940099098401,
      "can_relative_translation_from_partial_start_m": [
        0.0006817132234573364,
        -0.0005331635475158691,
        -0.0013569891452789307
      ],
      "can_to_box_relative_orientation_rad": 1.502918817686759,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.012615490704774857,
        0.012615490704774857
      ],
      "left_finger_qf_audit_only": [
        6.8185625076293945,
        -6.818591594696045
      ],
      "left_finger_qvel_mps": [
        -0.0026605245657265186,
        0.002035018987953663
      ],
      "linear_speed_mps": 0.0013168149704075652,
      "local_corner_max_m": [
        0.05240420848676569,
        0.20214005058443785,
        0.03641899683998662
      ],
      "local_corner_min_m": [
        -0.05250213366402734,
        0.1296241833005526,
        -0.03617325028833607
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764614942734566,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.113942272991507,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025349656755238856,
      "step_index": 2111,
      "timestamp_seconds": 8.444000401068479,
      "trace_row": 2111,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09737465527093649,
      "vertical_lower_margin_m": 0.10785878798705123,
      "vertical_upper_margin_m": -0.09737465527093649
    },
    {
      "actual_left_finger_qpos_m": [
        0.02313326485455036,
        0.02207397110760212
      ],
      "angular_speed_rps": 0.006624217095660424,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -4.676350043897326e-05,
        0.16587679047181414,
        0.0001233285198041223
      ],
      "can_pose": [
        -0.2929142713546753,
        -0.15269114077091217,
        0.9425771832466125,
        0.0011686851503327489,
        0.7006824612617493,
        0.04764831066131592,
        0.7118796110153198
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010325486399528305,
      "can_relative_translation_from_partial_start_m": [
        0.0006838738918304443,
        -0.0005379915237426758,
        -0.0013576745986938477
      ],
      "can_to_box_relative_orientation_rad": 1.5029300860909858,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.012778191827237606,
        0.012778191827237606
      ],
      "left_finger_qf_audit_only": [
        6.818587303161621,
        -6.818613052368164
      ],
      "left_finger_qvel_mps": [
        -0.0026614712551236153,
        0.002067586872726679
      ],
      "linear_speed_mps": 0.0013334093038803534,
      "local_corner_max_m": [
        0.05240679033485046,
        0.20213405809971718,
        0.03642040718505768
      ],
      "local_corner_min_m": [
        -0.05250031733572841,
        0.1296195228439111,
        -0.036173750145449435
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764569418336681,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394277284862037,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025347074907154085,
      "step_index": 2112,
      "timestamp_seconds": 8.448000401258469,
      "trace_row": 2112,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09736866278621582,
      "vertical_lower_margin_m": 0.10785412753040974,
      "vertical_upper_margin_m": -0.09736866278621582
    },
    {
      "actual_left_finger_qpos_m": [
        0.023128295317292213,
        0.022079888731241226
      ],
      "angular_speed_rps": 0.006814832758600143,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -4.456066856003971e-05,
        0.16587176367797374,
        0.00012383979879920792
      ],
      "can_pose": [
        -0.2929149568080902,
        -0.15268898010253906,
        0.9425726532936096,
        0.0011560822604224086,
        0.7006828784942627,
        0.047653425484895706,
        0.7118788361549377
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010351440225901176,
      "can_relative_translation_from_partial_start_m": [
        0.0006860345602035522,
        -0.0005425214767456055,
        -0.0013583600521087646
      ],
      "can_to_box_relative_orientation_rad": 1.5029415134335997,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.012940892949700356,
        0.012940892949700356
      ],
      "left_finger_qf_audit_only": [
        6.818611145019531,
        -6.818641185760498
      ],
      "left_finger_qvel_mps": [
        -0.0026442985981702805,
        0.002059031743556261
      ],
      "linear_speed_mps": 0.0012663630495898977,
      "local_corner_max_m": [
        0.05240941144474978,
        0.2021284795608449,
        0.03642204217971795
      ],
      "local_corner_min_m": [
        -0.05249853278186989,
        0.12961504779510258,
        -0.036174362582119535
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764518290437172,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394338528529047,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025344453797254765,
      "step_index": 2113,
      "timestamp_seconds": 8.452000401448458,
      "trace_row": 2113,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09736308424734354,
      "vertical_lower_margin_m": 0.10784965248160122,
      "vertical_upper_margin_m": -0.09736308424734354
    },
    {
      "actual_left_finger_qpos_m": [
        0.023123284801840782,
        0.022085856646299362
      ],
      "angular_speed_rps": 0.006477917141809354,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -4.240194593693736e-05,
        0.16586637196776743,
        0.00012430301446580971
      ],
      "can_pose": [
        -0.2929156422615051,
        -0.15268686413764954,
        0.9425677061080933,
        0.0011442044051364064,
        0.7006829977035522,
        0.04765858128666878,
        0.7118784189224243
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010375846155562892,
      "can_relative_translation_from_partial_start_m": [
        0.0006881505250930786,
        -0.0005474686622619629,
        -0.0013590455055236816
      ],
      "can_to_box_relative_orientation_rad": 1.5029518357168508,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.013103594072163105,
        0.013103594072163105
      ],
      "left_finger_qf_audit_only": [
        6.818641662597656,
        -6.818671703338623
      ],
      "left_finger_qvel_mps": [
        -0.002850497607141733,
        0.002251827158033848
      ],
      "linear_speed_mps": 0.0013560465408694884,
      "local_corner_max_m": [
        0.05241199190710544,
        0.20212261650283136,
        0.0364236120735284
      ],
      "local_corner_min_m": [
        -0.05249679579897931,
        0.1296101274327035,
        -0.03617500604459678
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764471968870512,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394402874776771,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02534187333489911,
      "step_index": 2114,
      "timestamp_seconds": 8.456000401638448,
      "trace_row": 2114,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09735722118933,
      "vertical_lower_margin_m": 0.10784473211920215,
      "vertical_upper_margin_m": -0.09735722118933
    },
    {
      "actual_left_finger_qpos_m": [
        0.023118173703551292,
        0.022091757506132126
      ],
      "angular_speed_rps": 0.006403569118888628,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -4.024464496577007e-05,
        0.16586122252030933,
        0.00012518645854148192
      ],
      "can_pose": [
        -0.29291588068008423,
        -0.15268474817276,
        0.942562997341156,
        0.0011324791703373194,
        0.7006819844245911,
        0.047663573175668716,
        0.7118791937828064
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010398688384194804,
      "can_relative_translation_from_partial_start_m": [
        0.000690266489982605,
        -0.0005521774291992188,
        -0.0013592839241027832
      ],
      "can_to_box_relative_orientation_rad": 1.5029621891482736,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.013266295194625854,
        0.013266295194625854
      ],
      "left_finger_qf_audit_only": [
        6.8186564445495605,
        -6.818692207336426
      ],
      "left_finger_qvel_mps": [
        -0.0026952142361551523,
        0.002080874750390649
      ],
      "linear_speed_mps": 0.0012919615504381524,
      "local_corner_max_m": [
        0.05241455736017922,
        0.20211710583954035,
        0.03642568051305506
      ],
      "local_corner_min_m": [
        -0.05249504665011073,
        0.1296053392010783,
        -0.036175307595972095
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764383624462945,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394433029914303,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025339307881825326,
      "step_index": 2115,
      "timestamp_seconds": 8.460000401828438,
      "trace_row": 2115,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09735171052603898,
      "vertical_lower_margin_m": 0.10783994388757695,
      "vertical_upper_margin_m": -0.09735171052603898
    },
    {
      "actual_left_finger_qpos_m": [
        0.023113062605261803,
        0.02209777943789959
      ],
      "angular_speed_rps": 0.006786682708772589,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -3.8098618651061233e-05,
        0.16585581122865312,
        0.00012573403520416138
      ],
      "can_pose": [
        -0.29291653633117676,
        -0.15268264710903168,
        0.9425580501556396,
        0.0011200810549780726,
        0.7006825804710388,
        0.04766898229718208,
        0.71187824010849
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010424707041178647,
      "can_relative_translation_from_partial_start_m": [
        0.0006923675537109375,
        -0.0005571246147155762,
        -0.0013599395751953125
      ],
      "can_to_box_relative_orientation_rad": 1.5029729126731117,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.013428996317088604,
        0.013428996317088604
      ],
      "left_finger_qf_audit_only": [
        6.8186726570129395,
        -6.818697929382324
      ],
      "left_finger_qvel_mps": [
        -0.0026573596987873316,
        0.0020672446116805077
      ],
      "linear_speed_mps": 0.001353675295578474,
      "local_corner_max_m": [
        0.05241714589353186,
        0.20211115729083795,
        0.036427342751728875
      ],
      "local_corner_min_m": [
        -0.05249334313083398,
        0.12960046516646828,
        -0.03617587468132055
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764328866796677,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394489738449148,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02533671934847269,
      "step_index": 2116,
      "timestamp_seconds": 8.464000402018428,
      "trace_row": 2116,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09734576197733659,
      "vertical_lower_margin_m": 0.10783506985296692,
      "vertical_upper_margin_m": -0.09734576197733659
    },
    {
      "actual_left_finger_qpos_m": [
        0.02310802973806858,
        0.02210376411676407
      ],
      "angular_speed_rps": 0.005698869656412696,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -3.606558430824247e-05,
        0.16585060878895397,
        0.00012669613806465252
      ],
      "can_pose": [
        -0.29291650652885437,
        -0.1526806354522705,
        0.9425534009933472,
        0.001109028933569789,
        0.7006828784942627,
        0.04767172038555145,
        0.7118778228759766
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010446063267404585,
      "can_relative_translation_from_partial_start_m": [
        0.0006943792104721069,
        -0.0005617737770080566,
        -0.0013599097728729248
      ],
      "can_to_box_relative_orientation_rad": 1.5029853291771973,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.013591697439551353,
        0.013591697439551353
      ],
      "left_finger_qf_audit_only": [
        6.8186936378479,
        -6.818721771240234
      ],
      "left_finger_qvel_mps": [
        -0.002697551157325506,
        0.0021042381413280964
      ],
      "linear_speed_mps": 0.0012664507167475794,
      "local_corner_max_m": [
        0.05241940098231279,
        0.20210537770463466,
        0.03642918610308343
      ],
      "local_corner_min_m": [
        -0.052491532150929276,
        0.12959583987327328,
        -0.03617579382695413
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764232656510628,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394481653012506,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025334464259691755,
      "step_index": 2117,
      "timestamp_seconds": 8.468000402208418,
      "trace_row": 2117,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0973399823911333,
      "vertical_lower_margin_m": 0.10783044455977192,
      "vertical_upper_margin_m": -0.0973399823911333
    },
    {
      "actual_left_finger_qpos_m": [
        0.02310299128293991,
        0.02210969291627407
      ],
      "angular_speed_rps": 0.006178965384446199,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -3.403350702141372e-05,
        0.16584547787771065,
        0.00012755888879567578
      ],
      "can_pose": [
        -0.2929167151451111,
        -0.15267863869667053,
        0.9425487518310547,
        0.0010974480537697673,
        0.7006828784942627,
        0.047676023095846176,
        0.7118775248527527
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010469252109960756,
      "can_relative_translation_from_partial_start_m": [
        0.0006963759660720825,
        -0.0005664229393005371,
        -0.0013601183891296387
      ],
      "can_to_box_relative_orientation_rad": 1.5029963836562923,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.013754398562014103,
        0.013754398562014103
      ],
      "left_finger_qf_audit_only": [
        6.81870174407959,
        -6.818728446960449
      ],
      "left_finger_qvel_mps": [
        -0.0027398800011724234,
        0.0021714798640459776
      ],
      "linear_speed_mps": 0.0012660287628607678,
      "local_corner_max_m": [
        0.05242178443402801,
        0.20209975299109806,
        0.03643108861894512
      ],
      "local_corner_min_m": [
        -0.052489851448070834,
        0.12959120276432323,
        -0.036175970841353766
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07764146381437526,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139449935445247,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02533208080797654,
      "step_index": 2118,
      "timestamp_seconds": 8.472000402398407,
      "trace_row": 2118,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0973343576775967,
      "vertical_lower_margin_m": 0.10782580745082188,
      "vertical_upper_margin_m": -0.0973343576775967
    },
    {
      "actual_left_finger_qpos_m": [
        0.02309790439903736,
        0.022115647792816162
      ],
      "angular_speed_rps": 0.006546114281665861,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -3.185860467114221e-05,
        0.16584007821241709,
        0.00012829495673882807
      ],
      "can_pose": [
        -0.2929171919822693,
        -0.152676522731781,
        0.942543625831604,
        0.0010863358620554209,
        0.7006826996803284,
        0.04768293723464012,
        0.7118772268295288
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010493432849861178,
      "can_relative_translation_from_partial_start_m": [
        0.0006984919309616089,
        -0.0005715489387512207,
        -0.0013605952262878418
      ],
      "can_to_box_relative_orientation_rad": 1.5030031883150088,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.013917099684476852,
        0.013917099684476852
      ],
      "left_finger_qf_audit_only": [
        6.818716526031494,
        -6.818750381469727
      ],
      "left_finger_qvel_mps": [
        -0.0028354497626423836,
        0.0022174471523612738
      ],
      "linear_speed_mps": 0.0013915043234429287,
      "local_corner_max_m": [
        0.05242452671396,
        0.20209406092592253,
        0.036433017664023515
      ],
      "local_corner_min_m": [
        -0.05248824392330226,
        0.12958609549891165,
        -0.03617642775054586
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776407277464321,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394545045371679,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025329338528044545,
      "step_index": 2119,
      "timestamp_seconds": 8.476000402588397,
      "trace_row": 2119,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09732866561242116,
      "vertical_lower_margin_m": 0.10782070018541029,
      "vertical_upper_margin_m": -0.09732866561242116
    },
    {
      "actual_left_finger_qpos_m": [
        0.023092858493328094,
        0.022121604532003403
      ],
      "angular_speed_rps": 0.005650468648143565,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -2.993206728552078e-05,
        0.16583494811552746,
        0.00012937029402282363
      ],
      "can_pose": [
        -0.2929171025753021,
        -0.1526746302843094,
        0.9425389170646667,
        0.0010758200660347939,
        0.7006824016571045,
        0.04768706485629082,
        0.7118772864341736
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010514341573873988,
      "can_relative_translation_from_partial_start_m": [
        0.0007003843784332275,
        -0.0005762577056884766,
        -0.0013605058193206787
      ],
      "can_to_box_relative_orientation_rad": 1.5030129350305166,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.014079800806939602,
        0.014079800806939602
      ],
      "left_finger_qf_audit_only": [
        6.818720817565918,
        -6.818751335144043
      ],
      "left_finger_qvel_mps": [
        -0.002794952830299735,
        0.0021999964956194162
      ],
      "linear_speed_mps": 0.001268902938091701,
      "local_corner_max_m": [
        0.0524267903770462,
        0.20208852596270088,
        0.03643507879056884
      ],
      "local_corner_min_m": [
        -0.052486654511617215,
        0.12958137026835403,
        -0.036176338202523195
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763965240914811,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394536090569413,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025327074864958346,
      "step_index": 2120,
      "timestamp_seconds": 8.480000402778387,
      "trace_row": 2120,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09732313064919952,
      "vertical_lower_margin_m": 0.10781597495485268,
      "vertical_upper_margin_m": -0.09732313064919952
    },
    {
      "actual_left_finger_qpos_m": [
        0.02308780699968338,
        0.022127637639641762
      ],
      "angular_speed_rps": 0.005744337671496812,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -2.786309590674385e-05,
        0.16582962236355403,
        0.00013042571132737546
      ],
      "can_pose": [
        -0.29291701316833496,
        -0.15267258882522583,
        0.9425340890884399,
        0.001064869575202465,
        0.7006818056106567,
        0.04769046977162361,
        0.7118776440620422
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010535184727958074,
      "can_relative_translation_from_partial_start_m": [
        0.0007024258375167847,
        -0.0005810856819152832,
        -0.0013604164123535156
      ],
      "can_to_box_relative_orientation_rad": 1.5030243095673355,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.014242501929402351,
        0.014242501929402351
      ],
      "left_finger_qf_audit_only": [
        6.818717956542969,
        -6.818753719329834
      ],
      "left_finger_qvel_mps": [
        -0.0027687614783644676,
        0.002173077315092087
      ],
      "linear_speed_mps": 0.001310651093714966,
      "local_corner_max_m": [
        0.052429136702220075,
        0.20208275076593274,
        0.036437125412787985
      ],
      "local_corner_min_m": [
        -0.052484862894033535,
        0.12957649396117532,
        -0.036176273990133234
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763859699184356,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394529669330417,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025324728539784472,
      "step_index": 2121,
      "timestamp_seconds": 8.484000402968377,
      "trace_row": 2121,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09731735545243138,
      "vertical_lower_margin_m": 0.10781109864767396,
      "vertical_upper_margin_m": -0.09731735545243138
    },
    {
      "actual_left_finger_qpos_m": [
        0.02308257855474949,
        0.02213370054960251
      ],
      "angular_speed_rps": 0.005908790920193378,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -2.5852822940264364e-05,
        0.16582434217542796,
        0.00013150999517663742
      ],
      "can_pose": [
        -0.2929169237613678,
        -0.15267060697078705,
        0.9425293207168579,
        0.0010536029003560543,
        0.7006812691688538,
        0.04769398272037506,
        0.7118779420852661
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010556719771819432,
      "can_relative_translation_from_partial_start_m": [
        0.0007044076919555664,
        -0.0005858540534973145,
        -0.0013603270053863525
      ],
      "can_to_box_relative_orientation_rad": 1.5030359980757646,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0144052030518651,
        0.0144052030518651
      ],
      "left_finger_qf_audit_only": [
        6.818724155426025,
        -6.818751335144043
      ],
      "left_finger_qvel_mps": [
        -0.0027409950271248817,
        0.002117857104167342
      ],
      "linear_speed_mps": 0.001291150301882256,
      "local_corner_max_m": [
        0.05243143308658488,
        0.2020770017628709,
        0.0364392238498939
      ],
      "local_corner_min_m": [
        -0.052483138732465406,
        0.12957168258798502,
        -0.03617620385954062
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776375127079943,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394522656271155,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02532243215541967,
      "step_index": 2122,
      "timestamp_seconds": 8.488000403158367,
      "trace_row": 2122,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09731160644936955,
      "vertical_lower_margin_m": 0.10780628727448366,
      "vertical_upper_margin_m": -0.09731160644936955
    },
    {
      "actual_left_finger_qpos_m": [
        0.023077603429555893,
        0.0221396591514349
      ],
      "angular_speed_rps": 0.005746025609466081,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -2.3947832628989918e-05,
        0.16581910541217926,
        0.0001325748250688985
      ],
      "can_pose": [
        -0.2929168939590454,
        -0.15266874432563782,
        0.9425244331359863,
        0.0010432947892695665,
        0.7006815671920776,
        0.047699011862277985,
        0.7118772864341736
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010578604017797245,
      "can_relative_translation_from_partial_start_m": [
        0.0007062703371047974,
        -0.0005907416343688965,
        -0.0013602972030639648
      ],
      "can_to_box_relative_orientation_rad": 1.5030441920312068,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01456790417432785,
        0.01456790417432785
      ],
      "left_finger_qf_audit_only": [
        6.818730354309082,
        -6.818760395050049
      ],
      "left_finger_qvel_mps": [
        -0.0028884424827992916,
        0.0023017730563879013
      ],
      "linear_speed_mps": 0.0013076405112760169,
      "local_corner_max_m": [
        0.05243374984083787,
        0.20207136743926435,
        0.03644126560985084
      ],
      "local_corner_min_m": [
        -0.05248164550609585,
        0.12956684338509417,
        -0.03617611595971304
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763644787810203,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394513866288397,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025320115401166673,
      "step_index": 2123,
      "timestamp_seconds": 8.492000403348356,
      "trace_row": 2123,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09730597212576299,
      "vertical_lower_margin_m": 0.10780144807159281,
      "vertical_upper_margin_m": -0.09730597212576299
    },
    {
      "actual_left_finger_qpos_m": [
        0.023072456941008568,
        0.022145673632621765
      ],
      "angular_speed_rps": 0.005926822228801716,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -2.1974266108309992e-05,
        0.16581385493186684,
        0.0001339328311925625
      ],
      "can_pose": [
        -0.29291659593582153,
        -0.1526668220758438,
        0.9425194263458252,
        0.0010334245162084699,
        0.7006795406341553,
        0.04770502820611,
        0.7118789553642273
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010598116403181061,
      "can_relative_translation_from_partial_start_m": [
        0.0007081925868988037,
        -0.0005957484245300293,
        -0.0013599991798400879
      ],
      "can_to_box_relative_orientation_rad": 1.5030504565132599,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0147306052967906,
        0.0147306052967906
      ],
      "left_finger_qf_audit_only": [
        6.818726062774658,
        -6.818762302398682
      ],
      "left_finger_qvel_mps": [
        -0.0028876508586108685,
        0.002251741709187627
      ],
      "linear_speed_mps": 0.0013428469544536973,
      "local_corner_max_m": [
        0.05243621683789082,
        0.20206603021994607,
        0.03644383741550011
      ],
      "local_corner_min_m": [
        -0.05248016537010747,
        0.12956167964378762,
        -0.03617597175311499
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763508987197837,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394499445628592,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025317648404113727,
      "step_index": 2124,
      "timestamp_seconds": 8.496000403538346,
      "trace_row": 2124,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09730063490644471,
      "vertical_lower_margin_m": 0.10779628433028626,
      "vertical_upper_margin_m": -0.09730063490644471
    },
    {
      "actual_left_finger_qpos_m": [
        0.023067304864525795,
        0.02215171791613102
      ],
      "angular_speed_rps": 0.005332530635085075,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -2.0175541381117768e-05,
        0.16580868300944795,
        0.00013515631213589785
      ],
      "can_pose": [
        -0.29291626811027527,
        -0.15266504883766174,
        0.9425147175788879,
        0.0010232571512460709,
        0.7006789445877075,
        0.0477081723511219,
        0.711879312992096
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010617454305646831,
      "can_relative_translation_from_partial_start_m": [
        0.0007099658250808716,
        -0.0006004571914672852,
        -0.0013596713542938232
      ],
      "can_to_box_relative_orientation_rad": 1.503061041972336,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01489330641925335,
        0.01489330641925335
      ],
      "left_finger_qf_audit_only": [
        6.81872034072876,
        -6.81875467300415
      ],
      "left_finger_qvel_mps": [
        -0.0029816238675266504,
        0.0023768055252730846
      ],
      "linear_speed_mps": 0.0012605635370078409,
      "local_corner_max_m": [
        0.052438271603410386,
        0.2020604432263995,
        0.036445982938743404
      ],
      "local_corner_min_m": [
        -0.052478622686172594,
        0.12955692279249642,
        -0.03617567031447161
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763386639103503,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394469301764254,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02531559363859416,
      "step_index": 2125,
      "timestamp_seconds": 8.500000403728336,
      "trace_row": 2125,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09729504791289813,
      "vertical_lower_margin_m": 0.10779152747899506,
      "vertical_upper_margin_m": -0.09729504791289813
    },
    {
      "actual_left_finger_qpos_m": [
        0.023062266409397125,
        0.0221577025949955
      ],
      "angular_speed_rps": 0.005408584936686973,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -1.8165557629512552e-05,
        0.16580328816416545,
        0.00013658255464421565
      ],
      "can_pose": [
        -0.2929157614707947,
        -0.15266306698322296,
        0.9425097703933716,
        0.0010130245937034488,
        0.7006783485412598,
        0.04771161079406738,
        0.7118796706199646
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01063712462059356,
      "can_relative_translation_from_partial_start_m": [
        0.0007119476795196533,
        -0.0006054043769836426,
        -0.0013591647148132324
      ],
      "can_to_box_relative_orientation_rad": 1.503071321969323,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.015056007541716099,
        0.015056007541716099
      ],
      "left_finger_qf_audit_only": [
        6.818704605102539,
        -6.818747043609619
      ],
      "left_finger_qvel_mps": [
        -0.002835205290466547,
        0.0021954646799713373
      ],
      "linear_speed_mps": 0.0013383542223240781,
      "local_corner_max_m": [
        0.0524405618463451,
        0.2020546473828536,
        0.036448355320368386
      ],
      "local_corner_min_m": [
        -0.05247689296160413,
        0.1295519289454773,
        -0.036175190211079955
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763244014852672,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394421291425089,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025313303395659445,
      "step_index": 2126,
      "timestamp_seconds": 8.504000403918326,
      "trace_row": 2126,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09728925206935225,
      "vertical_lower_margin_m": 0.10778653363197593,
      "vertical_upper_margin_m": -0.09728925206935225
    },
    {
      "actual_left_finger_qpos_m": [
        0.023057011887431145,
        0.022163834422826767
      ],
      "angular_speed_rps": 0.005557069065290197,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -1.6177119169902276e-05,
        0.16579786014697062,
        0.00013801392012458003
      ],
      "can_pose": [
        -0.2929152846336365,
        -0.15266111493110657,
        0.9425047039985657,
        0.0010030843550339341,
        0.7006765007972717,
        0.04771595820784569,
        0.7118812203407288
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010655737638021407,
      "can_relative_translation_from_partial_start_m": [
        0.0007138997316360474,
        -0.0006104707717895508,
        -0.0013586878776550293
      ],
      "can_to_box_relative_orientation_rad": 1.503079962665217,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.015218708664178848,
        0.015218708664178848
      ],
      "left_finger_qf_audit_only": [
        6.818697452545166,
        -6.818728446960449
      ],
      "left_finger_qvel_mps": [
        -0.0028665836434811354,
        0.0022690279874950647
      ],
      "linear_speed_mps": 0.0013625856543708174,
      "local_corner_max_m": [
        0.05244290580937652,
        0.2020490101436192,
        0.036450879669183256
      ],
      "local_corner_min_m": [
        -0.0524752600477163,
        0.12954671015032204,
        -0.036174851828934096
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07763100878304635,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394387453210503,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025310959432628025,
      "step_index": 2127,
      "timestamp_seconds": 8.508000404108316,
      "trace_row": 2127,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09728361483011784,
      "vertical_lower_margin_m": 0.10778131483682069,
      "vertical_upper_margin_m": -0.09728361483011784
    },
    {
      "actual_left_finger_qpos_m": [
        0.02305195853114128,
        0.02216975949704647
      ],
      "angular_speed_rps": 0.0047765331146454445,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -1.4465207690217419e-05,
        0.16579261188061734,
        0.00013946416057664113
      ],
      "can_pose": [
        -0.29291465878486633,
        -0.15265943109989166,
        0.9424998164176941,
        0.0009941979078575969,
        0.7006757259368896,
        0.04771934449672699,
        0.711881697177887
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010672915337890719,
      "can_relative_translation_from_partial_start_m": [
        0.0007155835628509521,
        -0.0006153583526611328,
        -0.0013580620288848877
      ],
      "can_to_box_relative_orientation_rad": 1.5030883462105227,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.015381409786641598,
        0.015381409786641598
      ],
      "left_finger_qf_audit_only": [
        6.818691253662109,
        -6.818725109100342
      ],
      "left_finger_qvel_mps": [
        -0.0028728574980050325,
        0.0022319969721138477
      ],
      "linear_speed_mps": 0.0013018116809806694,
      "local_corner_max_m": [
        0.052444894329505026,
        0.20204345887512165,
        0.0364531968877404
      ],
      "local_corner_min_m": [
        -0.05247382474488549,
        0.12954176488611302,
        -0.03617426856658712
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762955854259429,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394329126975805,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02530897091249952,
      "step_index": 2128,
      "timestamp_seconds": 8.512000404298306,
      "trace_row": 2128,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09727806356162029,
      "vertical_lower_margin_m": 0.10777636957261166,
      "vertical_upper_margin_m": -0.09727806356162029
    },
    {
      "actual_left_finger_qpos_m": [
        0.023046715185046196,
        0.022175919264554977
      ],
      "angular_speed_rps": 0.005384297269267801,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -1.2542870466231149e-05,
        0.1657874144587288,
        0.00014086684918063197
      ],
      "can_pose": [
        -0.29291418194770813,
        -0.15265753865242004,
        0.9424950480461121,
        0.0009840677957981825,
        0.700675368309021,
        0.04772297292947769,
        0.7118819355964661
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010692745293709765,
      "can_relative_translation_from_partial_start_m": [
        0.0007174760103225708,
        -0.0006201267242431641,
        -0.0013575851917266846
      ],
      "can_to_box_relative_orientation_rad": 1.503098219405734,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.015544110909104347,
        0.015544110909104347
      ],
      "left_finger_qf_audit_only": [
        6.818671703338623,
        -6.818698883056641
      ],
      "left_finger_qvel_mps": [
        -0.002865410875529051,
        0.00227168295532465
      ],
      "linear_speed_mps": 0.0012880725942968623,
      "local_corner_max_m": [
        0.05244711221893508,
        0.20203786155942982,
        0.036455536095239605
      ],
      "local_corner_min_m": [
        -0.05247219795986757,
        0.12953696735802778,
        -0.03617380239687834
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776281558539903,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394282510004927,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025306753023069464,
      "step_index": 2129,
      "timestamp_seconds": 8.516000404488295,
      "trace_row": 2129,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09727246624592846,
      "vertical_lower_margin_m": 0.10777157204452642,
      "vertical_upper_margin_m": -0.09727246624592846
    },
    {
      "actual_left_finger_qpos_m": [
        0.02304164692759514,
        0.022181963548064232
      ],
      "angular_speed_rps": 0.005175761172058879,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -1.0900873507857511e-05,
        0.16578223612026444,
        0.0001423765504175445
      ],
      "can_pose": [
        -0.292913556098938,
        -0.1526559293270111,
        0.9424902200698853,
        0.0009747485164552927,
        0.7006736397743225,
        0.04772688075900078,
        0.7118833661079407
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01071011777294644,
      "can_relative_translation_from_partial_start_m": [
        0.0007190853357315063,
        -0.0006249547004699707,
        -0.001356959342956543
      ],
      "can_to_box_relative_orientation_rad": 1.5031065486076518,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01570681296288967,
        0.01570681296288967
      ],
      "left_finger_qf_audit_only": [
        6.818666934967041,
        -6.818698406219482
      ],
      "left_finger_qvel_mps": [
        -0.002902816981077194,
        0.002265341579914093
      ],
      "linear_speed_mps": 0.0012818679462028135,
      "local_corner_max_m": [
        0.05244907365671708,
        0.2020324754502799,
        0.036458058060135023
      ],
      "local_corner_min_m": [
        -0.0524708754037328,
        0.12953199679024896,
        -0.036173304959299935
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762664615275339,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394232766247087,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025304791585287464,
      "step_index": 2130,
      "timestamp_seconds": 8.520000404678285,
      "trace_row": 2130,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09726708013677855,
      "vertical_lower_margin_m": 0.1077666014767476,
      "vertical_upper_margin_m": -0.09726708013677855
    },
    {
      "actual_left_finger_qpos_m": [
        0.02303648367524147,
        0.022187959402799606
      ],
      "angular_speed_rps": 0.004533897453598966,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -8.95177980073103e-06,
        0.16577686674580594,
        0.00014394477220963653
      ],
      "can_pose": [
        -0.29291269183158875,
        -0.1526539921760559,
        0.9424853324890137,
        0.0009658693452365696,
        0.7006729245185852,
        0.04772846773266792,
        0.7118839621543884
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010725973056535193,
      "can_relative_translation_from_partial_start_m": [
        0.0007210224866867065,
        -0.0006298422813415527,
        -0.0013560950756072998
      ],
      "can_to_box_relative_orientation_rad": 1.5031173826161006,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.015869515016674995,
        0.015869515016674995
      ],
      "left_finger_qf_audit_only": [
        6.818645477294922,
        -6.8186774253845215
      ],
      "left_finger_qvel_mps": [
        -0.00279435608536005,
        0.002157122828066349
      ],
      "linear_speed_mps": 0.001332008726363688,
      "local_corner_max_m": [
        0.05245115043614218,
        0.2020266941886838,
        0.03646037361482163
      ],
      "local_corner_min_m": [
        -0.05246905399574364,
        0.12952703930292808,
        -0.036172484070402355
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776250779309613,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394150677357329,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025302714805862367,
      "step_index": 2131,
      "timestamp_seconds": 8.524000404868275,
      "trace_row": 2131,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09726129887518244,
      "vertical_lower_margin_m": 0.10776164398942673,
      "vertical_upper_margin_m": -0.09726129887518244
    },
    {
      "actual_left_finger_qpos_m": [
        0.02303122915327549,
        0.022194162011146545
      ],
      "angular_speed_rps": 0.005657650964078817,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -7.237292573070153e-06,
        0.16577163949464968,
        0.00014551821490565997
      ],
      "can_pose": [
        -0.2929121255874634,
        -0.1526523232460022,
        0.9424803853034973,
        0.0009561458136886358,
        0.7006711363792419,
        0.047733813524246216,
        0.7118852734565735
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010745136110728259,
      "can_relative_translation_from_partial_start_m": [
        0.0007226914167404175,
        -0.0006347894668579102,
        -0.0013555288314819336
      ],
      "can_to_box_relative_orientation_rad": 1.5031243351483659,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01603221707046032,
        0.01603221707046032
      ],
      "left_finger_qf_audit_only": [
        6.818638801574707,
        -6.818660259246826
      ],
      "left_finger_qvel_mps": [
        -0.0028049801476299763,
        0.0022053327411413193
      ],
      "linear_speed_mps": 0.0013129309256138379,
      "local_corner_max_m": [
        0.05245330322216177,
        0.20202132000465534,
        0.03646308065179693
      ],
      "local_corner_min_m": [
        -0.05246777780730788,
        0.12952195898464403,
        -0.03617204422198561
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762350448826527,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394106692515654,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02530056201984278,
      "step_index": 2132,
      "timestamp_seconds": 8.528000405058265,
      "trace_row": 2132,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09725592469115397,
      "vertical_lower_margin_m": 0.10775656367114267,
      "vertical_upper_margin_m": -0.09725592469115397
    },
    {
      "actual_left_finger_qpos_m": [
        0.023026127368211746,
        0.02220017835497856
      ],
      "angular_speed_rps": 0.004961525558444713,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -5.528558656958671e-06,
        0.16576661280591176,
        0.00014709803249318698
      ],
      "can_pose": [
        -0.29291144013404846,
        -0.1526506543159485,
        0.9424756169319153,
        0.0009474765392951667,
        0.7006701827049255,
        0.047738492488861084,
        0.7118859887123108
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010762703146031064,
      "can_relative_translation_from_partial_start_m": [
        0.0007243603467941284,
        -0.0006395578384399414,
        -0.0013548433780670166
      ],
      "can_to_box_relative_orientation_rad": 1.503130648530349,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.016194919124245644,
        0.016194919124245644
      ],
      "left_finger_qf_audit_only": [
        6.818624973297119,
        -6.8186540603637695
      ],
      "left_finger_qvel_mps": [
        -0.0028790398500859737,
        0.0022385194897651672
      ],
      "linear_speed_mps": 0.001274571962056414,
      "local_corner_max_m": [
        0.05245539497526028,
        0.20201610434331363,
        0.03646561789299313
      ],
      "local_corner_min_m": [
        -0.05246645209257417,
        0.1295171212685099,
        -0.036171421828006756
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762192467067774,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11394044453117769,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02529847026674427,
      "step_index": 2133,
      "timestamp_seconds": 8.532000405248255,
      "trace_row": 2133,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09725070902981227,
      "vertical_lower_margin_m": 0.10775172595500854,
      "vertical_upper_margin_m": -0.09725070902981227
    },
    {
      "actual_left_finger_qpos_m": [
        0.023020999506115913,
        0.022206218913197517
      ],
      "angular_speed_rps": 0.004395811035361664,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -3.740736655988286e-06,
        0.16576110518886722,
        0.00014866273717062395
      ],
      "can_pose": [
        -0.2929105758666992,
        -0.15264888107776642,
        0.9424705505371094,
        0.0009389271726831794,
        0.700669527053833,
        0.04774035885930061,
        0.7118865251541138
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010778268489401378,
      "can_relative_translation_from_partial_start_m": [
        0.0007261335849761963,
        -0.0006446242332458496,
        -0.0013539791107177734
      ],
      "can_to_box_relative_orientation_rad": 1.5031406185159741,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.016357621178030968,
        0.016357621178030968
      ],
      "left_finger_qf_audit_only": [
        6.818607330322266,
        -6.818637371063232
      ],
      "left_finger_qvel_mps": [
        -0.002831027377396822,
        0.002187067409977317
      ],
      "linear_speed_mps": 0.0013592204848419853,
      "local_corner_max_m": [
        0.052457333592971445,
        0.20201021781782957,
        0.03646792191565046
      ],
      "local_corner_min_m": [
        -0.05246481506628342,
        0.12951199255990486,
        -0.03617059644130921
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762035996600031,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393961914448014,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025296531649033102,
      "step_index": 2134,
      "timestamp_seconds": 8.536000405438244,
      "trace_row": 2134,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09724482250432821,
      "vertical_lower_margin_m": 0.10774659724640351,
      "vertical_upper_margin_m": -0.09724482250432821
    },
    {
      "actual_left_finger_qpos_m": [
        0.023015758022665977,
        0.02221229486167431
      ],
      "angular_speed_rps": 0.004766962332735215,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -2.144586501662271e-06,
        0.16575584202087779,
        0.00015032497796196864
      ],
      "can_pose": [
        -0.29290974140167236,
        -0.15264731645584106,
        0.942465603351593,
        0.0009303116821683943,
        0.700668215751648,
        0.047744106501340866,
        0.7118874788284302
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0107947938351915,
      "can_relative_translation_from_partial_start_m": [
        0.0007276982069015503,
        -0.000649571418762207,
        -0.001353144645690918
      ],
      "can_to_box_relative_orientation_rad": 1.503148123966865,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.016520323231816292,
        0.016520323231816292
      ],
      "left_finger_qf_audit_only": [
        6.818586349487305,
        -6.818617820739746
      ],
      "left_finger_qvel_mps": [
        -0.002973710186779499,
        0.002337514655664563
      ],
      "linear_speed_mps": 0.0013138449194999733,
      "local_corner_max_m": [
        0.05245923629685861,
        0.20200473998163826,
        0.03647050112004935
      ],
      "local_corner_min_m": [
        -0.05246352546986194,
        0.1295069440601173,
        -0.03616985116412541
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07761869772520896,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393887386729634,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025294628945145933,
      "step_index": 2135,
      "timestamp_seconds": 8.540000405628234,
      "trace_row": 2135,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0972393446681369,
      "vertical_lower_margin_m": 0.10774154874661596,
      "vertical_upper_margin_m": -0.0972393446681369
    },
    {
      "actual_left_finger_qpos_m": [
        0.023010678589344025,
        0.022218337282538414
      ],
      "angular_speed_rps": 0.004770767935315021,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -4.2074046069373594e-07,
        0.16575085321509997,
        0.00015218137415734523
      ],
      "can_pose": [
        -0.292908638715744,
        -0.15264561772346497,
        0.9424609541893005,
        0.0009219863568432629,
        0.7006656527519226,
        0.047747138887643814,
        0.711889922618866
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010808967056188957,
      "can_relative_translation_from_partial_start_m": [
        0.0007293969392776489,
        -0.0006542205810546875,
        -0.0013520419597625732
      ],
      "can_to_box_relative_orientation_rad": 1.5031562237556613,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.016683025285601616,
        0.016683025285601616
      ],
      "left_finger_qf_audit_only": [
        6.8185577392578125,
        -6.818592071533203
      ],
      "left_finger_qvel_mps": [
        -0.0029479828663170338,
        0.002328544855117798
      ],
      "linear_speed_mps": 0.0012677814165176129,
      "local_corner_max_m": [
        0.05246120720438227,
        0.20199964071079368,
        0.03647332405857767
      ],
      "local_corner_min_m": [
        -0.052462048685303686,
        0.12950206571940626,
        -0.03616896131026298
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07761684132901359,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393798401343391,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025292658037622276,
      "step_index": 2136,
      "timestamp_seconds": 8.544000405818224,
      "trace_row": 2136,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09723424539729232,
      "vertical_lower_margin_m": 0.1077366704059049,
      "vertical_upper_margin_m": -0.09723424539729232
    },
    {
      "actual_left_finger_qpos_m": [
        0.02300545945763588,
        0.022224465385079384
      ],
      "angular_speed_rps": 0.004300109403618861,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.3309217674339902e-06,
        0.16574550871453675,
        0.0001541835632702937
      ],
      "can_pose": [
        -0.29290735721588135,
        -0.15264388918876648,
        0.9424559473991394,
        0.0009140135953202844,
        0.7006644010543823,
        0.04774993285536766,
        0.7118909358978271
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01082370604494507,
      "can_relative_translation_from_partial_start_m": [
        0.0007311254739761353,
        -0.0006592273712158203,
        -0.0013507604598999023
      ],
      "can_to_box_relative_orientation_rad": 1.5031640943235551,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01684572733938694,
        0.01684572733938694
      ],
      "left_finger_qf_audit_only": [
        6.818539142608643,
        -6.818574905395508
      ],
      "left_finger_qvel_mps": [
        -0.002994103357195854,
        0.002333202864974737
      ],
      "linear_speed_mps": 0.0013623972208563248,
      "local_corner_max_m": [
        0.05246318667796382,
        0.20199406350657245,
        0.036476136372456835
      ],
      "local_corner_min_m": [
        -0.05246052483442898,
        0.12949695392250105,
        -0.03616776924591625
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07761483913990064,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393679194908718,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025290678564040728,
      "step_index": 2137,
      "timestamp_seconds": 8.548000406008214,
      "trace_row": 2137,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09722866819307109,
      "vertical_lower_margin_m": 0.10773155860899969,
      "vertical_upper_margin_m": -0.09722866819307109
    },
    {
      "actual_left_finger_qpos_m": [
        0.02300027757883072,
        0.022230513393878937
      ],
      "angular_speed_rps": 0.004478569617205118,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.8711460730579397e-06,
        0.16574039841244648,
        0.00015598060793287072
      ],
      "can_pose": [
        -0.29290634393692017,
        -0.1526423841714859,
        0.9424510598182678,
        0.00090638711117208,
        0.7006627321243286,
        0.047754064202308655,
        0.7118924260139465
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010838384527527058,
      "can_relative_translation_from_partial_start_m": [
        0.0007326304912567139,
        -0.0006641149520874023,
        -0.0013497471809387207
      ],
      "can_to_box_relative_orientation_rad": 1.5031696500796314,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.017008429393172264,
        0.017008429393172264
      ],
      "left_finger_qf_audit_only": [
        6.818508625030518,
        -6.81854772567749
      ],
      "left_finger_qvel_mps": [
        -0.002941566053777933,
        0.002304809633642435
      ],
      "linear_speed_mps": 0.0013033671648436786,
      "local_corner_max_m": [
        0.05246506495688891,
        0.20198886832223084,
        0.036478849000183944
      ],
      "local_corner_min_m": [
        -0.05245932266474279,
        0.1294919285026621,
        -0.0361668877843182
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07761304209523806,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393591048748913,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02528880028511564,
      "step_index": 2138,
      "timestamp_seconds": 8.552000406198204,
      "trace_row": 2138,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09722347300872948,
      "vertical_lower_margin_m": 0.10772653318916076,
      "vertical_upper_margin_m": -0.09722347300872948
    },
    {
      "actual_left_finger_qpos_m": [
        0.02299518696963787,
        0.022236591205000877
      ],
      "angular_speed_rps": 0.004147401847416966,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        4.50637729054737e-06,
        0.16573504909981507,
        0.00015793669624053486
      ],
      "can_pose": [
        -0.2929050922393799,
        -0.15264077484607697,
        0.9424459934234619,
        0.0008989271591417491,
        0.7006612420082092,
        0.04775714874267578,
        0.711893618106842
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010852259087117892,
      "can_relative_translation_from_partial_start_m": [
        0.0007342398166656494,
        -0.0006691813468933105,
        -0.0013484954833984375
      ],
      "can_to_box_relative_orientation_rad": 1.5031763772152404,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.017171131446957588,
        0.017171131446957588
      ],
      "left_finger_qf_audit_only": [
        6.818485260009766,
        -6.818519115447998
      ],
      "left_finger_qvel_mps": [
        -0.002982278587296605,
        0.0023387866094708443
      ],
      "linear_speed_mps": 0.0013653073944240647,
      "local_corner_max_m": [
        0.05246695230804388,
        0.20198335746989993,
        0.036481619073529314
      ],
      "local_corner_min_m": [
        -0.052457939553462785,
        0.1294867407297302,
        -0.036165745681048245
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776110860069304,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393476838421918,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025286912933960667,
      "step_index": 2139,
      "timestamp_seconds": 8.556000406388193,
      "trace_row": 2139,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09721796215639857,
      "vertical_lower_margin_m": 0.10772134541622885,
      "vertical_upper_margin_m": -0.09721796215639857
    },
    {
      "actual_left_finger_qpos_m": [
        0.022989969700574875,
        0.022242732346057892
      ],
      "angular_speed_rps": 0.004344074298420967,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        6.122679044012758e-06,
        0.16572983390965657,
        0.00015981870144243793
      ],
      "can_pose": [
        -0.2929039001464844,
        -0.15263918042182922,
        0.9424411058425903,
        0.0008911966579034925,
        0.7006590962409973,
        0.04775979742407799,
        0.7118956446647644
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010865572790251752,
      "can_relative_translation_from_partial_start_m": [
        0.0007358342409133911,
        -0.0006740689277648926,
        -0.0013473033905029297
      ],
      "can_to_box_relative_orientation_rad": 1.5031841202814422,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.017333833500742912,
        0.017333833500742912
      ],
      "left_finger_qf_audit_only": [
        6.818456172943115,
        -6.818487167358398
      ],
      "left_finger_qvel_mps": [
        -0.002910246606916189,
        0.0022551938891410828
      ],
      "linear_speed_mps": 0.0013193681793710514,
      "local_corner_max_m": [
        0.052468784190061984,
        0.2019780066807556,
        0.0364843668643261
      ],
      "local_corner_min_m": [
        -0.05245653883197399,
        0.12948166113855752,
        -0.036164729461441225
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0776092040017285,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393375216461216,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025285081051942562,
      "step_index": 2140,
      "timestamp_seconds": 8.560000406578183,
      "trace_row": 2140,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09721261136725425,
      "vertical_lower_margin_m": 0.10771626582505617,
      "vertical_upper_margin_m": -0.09721261136725425
    },
    {
      "actual_left_finger_qpos_m": [
        0.02298491820693016,
        0.022248676046729088
      ],
      "angular_speed_rps": 0.004365474272289513,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        7.786295136508192e-06,
        0.16572480689933156,
        0.00016182021831662174
      ],
      "can_pose": [
        -0.2929026186466217,
        -0.1526375412940979,
        0.9424363970756531,
        0.0008833351312205195,
        0.700657308101654,
        0.047762736678123474,
        0.7118972539901733
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010879709574991929,
      "can_relative_translation_from_partial_start_m": [
        0.0007374733686447144,
        -0.0006787776947021484,
        -0.0013460218906402588
      ],
      "can_to_box_relative_orientation_rad": 1.5031916471504674,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.017496535554528236,
        0.017496535554528236
      ],
      "left_finger_qf_audit_only": [
        6.818424701690674,
        -6.818456172943115
      ],
      "left_finger_qvel_mps": [
        -0.0028350388165563345,
        0.0021902143489569426
      ],
      "linear_speed_mps": 0.0012869893445923554,
      "local_corner_max_m": [
        0.05247068742581246,
        0.2019728169363837,
        0.03648722930020337
      ],
      "local_corner_min_m": [
        -0.05245511483553944,
        0.12947679686227942,
        -0.03616358886357013
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07760720248485431,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393261156674106,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02528317781619209,
      "step_index": 2141,
      "timestamp_seconds": 8.564000406768173,
      "trace_row": 2141,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09720742162288233,
      "vertical_lower_margin_m": 0.10771140154877806,
      "vertical_upper_margin_m": -0.09720742162288233
    },
    {
      "actual_left_finger_qpos_m": [
        0.02297995053231716,
        0.022254668176174164
      ],
      "angular_speed_rps": 0.00475172272908999,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        9.360114312545464e-06,
        0.16571963011821578,
        0.00016366117986071904
      ],
      "can_pose": [
        -0.2929016649723053,
        -0.15263602137565613,
        0.9424312710762024,
        0.0008762446232140064,
        0.7006561160087585,
        0.04776891693472862,
        0.7118979096412659
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010895616702738116,
      "can_relative_translation_from_partial_start_m": [
        0.0007389932870864868,
        -0.000683903694152832,
        -0.0013450682163238525
      ],
      "can_to_box_relative_orientation_rad": 1.5031935957155864,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01765923760831356,
        0.01765923760831356
      ],
      "left_finger_qf_audit_only": [
        6.8183913230896,
        -6.818424701690674
      ],
      "left_finger_qvel_mps": [
        -0.002892585936933756,
        0.0022341341245919466
      ],
      "linear_speed_mps": 0.001357744322808465,
      "local_corner_max_m": [
        0.0524727693591997,
        0.20196765563216945,
        0.03649003330935241
      ],
      "local_corner_min_m": [
        -0.05245404913057461,
        0.1294716046042621,
        -0.03616271094963097
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07760536152331021,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139317336528019,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025281095882804847,
      "step_index": 2142,
      "timestamp_seconds": 8.568000406958163,
      "trace_row": 2142,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09720226031866809,
      "vertical_lower_margin_m": 0.10770620929076075,
      "vertical_upper_margin_m": -0.09720226031866809
    },
    {
      "actual_left_finger_qpos_m": [
        0.022974951192736626,
        0.02226056158542633
      ],
      "angular_speed_rps": 0.00435976458896933,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.0812334405752022e-05,
        0.1657146423101985,
        0.00016562000510439434
      ],
      "can_pose": [
        -0.2929004430770874,
        -0.1526346057653427,
        0.9424264430999756,
        0.0008693840936757624,
        0.7006536722183228,
        0.047773174941539764,
        0.7119001150131226
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010908391672048318,
      "can_relative_translation_from_partial_start_m": [
        0.0007404088973999023,
        -0.0006887316703796387,
        -0.001343846321105957
      ],
      "can_to_box_relative_orientation_rad": 1.5031978744570929,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.017821939662098885,
        0.017821939662098885
      ],
      "left_finger_qf_audit_only": [
        6.818367004394531,
        -6.818398475646973
      ],
      "left_finger_qvel_mps": [
        -0.0031255565118044615,
        0.0024794009514153004
      ],
      "linear_speed_mps": 0.0012943708023376989,
      "local_corner_max_m": [
        0.05247457049591073,
        0.20196271134325883,
        0.036492929822838305
      ],
      "local_corner_min_m": [
        -0.05245294582709925,
        0.12946657327713817,
        -0.036161689812629516
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07760340269806654,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393071251580045,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02527929474609382,
      "step_index": 2143,
      "timestamp_seconds": 8.572000407148153,
      "trace_row": 2143,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09719731602975747,
      "vertical_lower_margin_m": 0.10770117796363682,
      "vertical_upper_margin_m": -0.09719731602975747
    },
    {
      "actual_left_finger_qpos_m": [
        0.022970274090766907,
        0.022266298532485962
      ],
      "angular_speed_rps": 0.0036849224985560135,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.2447436809170931e-05,
        0.16570963019926432,
        0.00016762026852235046
      ],
      "can_pose": [
        -0.29289883375167847,
        -0.1526329666376114,
        0.9424218535423279,
        0.0008631493546999991,
        0.7006508708000183,
        0.04777289554476738,
        0.7119028568267822
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010916368765731214,
      "can_relative_translation_from_partial_start_m": [
        0.0007420480251312256,
        -0.0006933212280273438,
        -0.0013422369956970215
      ],
      "can_to_box_relative_orientation_rad": 1.5032074384552905,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01798464171588421,
        0.01798464171588421
      ],
      "left_finger_qf_audit_only": [
        6.818315505981445,
        -6.818360805511475
      ],
      "left_finger_qvel_mps": [
        -0.003031743224710226,
        0.0023909283336251974
      ],
      "linear_speed_mps": 0.0012830799100897287,
      "local_corner_max_m": [
        0.05247618018159059,
        0.20195754343317796,
        0.03649555883783295
      ],
      "local_corner_min_m": [
        -0.05245128530797222,
        0.1294617169653507,
        -0.03616031830078825
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07760140243464858,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392934100395918,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02527768506041396,
      "step_index": 2144,
      "timestamp_seconds": 8.576000407338142,
      "trace_row": 2144,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0971921481196766,
      "vertical_lower_margin_m": 0.10769632165184934,
      "vertical_upper_margin_m": -0.0971921481196766
    },
    {
      "actual_left_finger_qpos_m": [
        0.022965433076024055,
        0.02227207086980343
      ],
      "angular_speed_rps": 0.004210129049301895,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.403849501324661e-05,
        0.16570459597020437,
        0.00016970989603459774
      ],
      "can_pose": [
        -0.29289737343788147,
        -0.15263140201568604,
        0.9424170255661011,
        0.0008566997712478042,
        0.7006475925445557,
        0.047776006162166595,
        0.711905837059021
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010926855945192588,
      "can_relative_translation_from_partial_start_m": [
        0.0007436126470565796,
        -0.0006981492042541504,
        -0.0013407766819000244
      ],
      "can_to_box_relative_orientation_rad": 1.5032126960222612,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.018147343769669533,
        0.018147343769669533
      ],
      "left_finger_qf_audit_only": [
        6.818265438079834,
        -6.818306922912598
      ],
      "left_finger_qvel_mps": [
        -0.002859140280634165,
        0.0022400892339646816
      ],
      "linear_speed_mps": 0.001320272461279518,
      "local_corner_max_m": [
        0.052478025889910684,
        0.20195258473908728,
        0.036498550934370766
      ],
      "local_corner_min_m": [
        -0.05244994889988419,
        0.12945660720132146,
        -0.03615913114230157
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759931280713633,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139281538454725,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025275839352093862,
      "step_index": 2145,
      "timestamp_seconds": 8.580000407528132,
      "trace_row": 2145,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09718718942558592,
      "vertical_lower_margin_m": 0.1076912118878201,
      "vertical_upper_margin_m": -0.09718718942558592
    },
    {
      "actual_left_finger_qpos_m": [
        0.022960765287280083,
        0.022277623414993286
      ],
      "angular_speed_rps": 0.004060990099929246,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.548089597352975e-05,
        0.16569969079863145,
        0.0001715091396066737
      ],
      "can_pose": [
        -0.2928963005542755,
        -0.1526300013065338,
        0.9424121975898743,
        0.0008505738223902881,
        0.7006458044052124,
        0.047780804336071014,
        0.7119073271751404
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010939435496613642,
      "can_relative_translation_from_partial_start_m": [
        0.0007450133562088013,
        -0.000702977180480957,
        -0.0013397037982940674
      ],
      "can_to_box_relative_orientation_rad": 1.5032151455048917,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.018310045823454857,
        0.018310045823454857
      ],
      "left_finger_qf_audit_only": [
        6.818229675292969,
        -6.818264961242676
      ],
      "left_finger_qvel_mps": [
        -0.0028871195390820503,
        0.002284778282046318
      ],
      "linear_speed_mps": 0.0012850685122218195,
      "local_corner_max_m": [
        0.052479862155569545,
        0.20194773896402674,
        0.036501217344642956
      ],
      "local_corner_min_m": [
        -0.052448900363622486,
        0.12945164263323616,
        -0.03615819906542961
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759751356356426,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392722176860054,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025274003086435,
      "step_index": 2146,
      "timestamp_seconds": 8.584000407718122,
      "trace_row": 2146,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09718234365052537,
      "vertical_lower_margin_m": 0.1076862473197348,
      "vertical_upper_margin_m": -0.09718234365052537
    },
    {
      "actual_left_finger_qpos_m": [
        0.022956356406211853,
        0.022283069789409637
      ],
      "angular_speed_rps": 0.0037651897355132813,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.7024528358972058e-05,
        0.16569498892060197,
        0.0001732726584026678
      ],
      "can_pose": [
        -0.29289504885673523,
        -0.15262846648693085,
        0.9424078464508057,
        0.0008439843077212572,
        0.7006433010101318,
        0.04778195917606354,
        0.7119097113609314
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010949417134351186,
      "can_relative_translation_from_partial_start_m": [
        0.0007465481758117676,
        -0.0007073283195495605,
        -0.0013384521007537842
      ],
      "can_to_box_relative_orientation_rad": 1.5032232641692667,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01847274787724018,
        0.01847274787724018
      ],
      "left_finger_qf_audit_only": [
        6.818179607391357,
        -6.818215847015381
      ],
      "left_finger_qvel_mps": [
        -0.0027863651048392057,
        0.0021639184560626745
      ],
      "linear_speed_mps": 0.0011951680574619106,
      "local_corner_max_m": [
        0.05248149858746831,
        0.20194291642163076,
        0.03650370158928462
      ],
      "local_corner_min_m": [
        -0.05244744953075037,
        0.12944706141957318,
        -0.036157156272479285
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759575004476826,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392617897565022,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025272366654536235,
      "step_index": 2147,
      "timestamp_seconds": 8.588000407908112,
      "trace_row": 2147,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0971775211081294,
      "vertical_lower_margin_m": 0.10768166610607183,
      "vertical_upper_margin_m": -0.0971775211081294
    },
    {
      "actual_left_finger_qpos_m": [
        0.02295203134417534,
        0.022288411855697632
      ],
      "angular_speed_rps": 0.003454795772111946,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.8506685715846682e-05,
        0.16569038742027464,
        0.00017493371847038253
      ],
      "can_pose": [
        -0.29289382696151733,
        -0.15262699127197266,
        0.9424035549163818,
        0.0008382287924177945,
        0.7006406188011169,
        0.047782883048057556,
        0.7119122743606567
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010957622979182463,
      "can_relative_translation_from_partial_start_m": [
        0.0007480233907699585,
        -0.0007116198539733887,
        -0.0013372302055358887
      ],
      "can_to_box_relative_orientation_rad": 1.5032304819628852,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.018635449931025505,
        0.018635449931025505
      ],
      "left_finger_qf_audit_only": [
        6.818138122558594,
        -6.818174839019775
      ],
      "left_finger_qvel_mps": [
        -0.0027314070612192154,
        0.002123088575899601
      ],
      "linear_speed_mps": 0.0011749083131562322,
      "local_corner_max_m": [
        0.05248305485043647,
        0.2019382507658889,
        0.03650602830224381
      ],
      "local_corner_min_m": [
        -0.05244604147900478,
        0.1294425240746604,
        -0.036156160865303044
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759408898470055,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392518356847398,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025270810391568074,
      "step_index": 2148,
      "timestamp_seconds": 8.592000408098102,
      "trace_row": 2148,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09717285545238753,
      "vertical_lower_margin_m": 0.10767712876115904,
      "vertical_upper_margin_m": -0.09717285545238753
    },
    {
      "actual_left_finger_qpos_m": [
        0.02294796146452427,
        0.022293513640761375
      ],
      "angular_speed_rps": 0.003045863367994448,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.9859467389859997e-05,
        0.16568599797663675,
        0.00017643214888823922
      ],
      "can_pose": [
        -0.29289284348487854,
        -0.1526256650686264,
        0.942399263381958,
        0.0008335334714502096,
        0.7006388902664185,
        0.047785963863134384,
        0.7119138836860657
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010966459385770051,
      "can_relative_translation_from_partial_start_m": [
        0.0007493495941162109,
        -0.0007159113883972168,
        -0.0013362467288970947
      ],
      "can_to_box_relative_orientation_rad": 1.5032331877332408,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01879815198481083,
        0.01879815198481083
      ],
      "left_finger_qf_audit_only": [
        6.8180952072143555,
        -6.818127632141113
      ],
      "left_finger_qvel_mps": [
        -0.002672518603503704,
        0.002075621858239174
      ],
      "linear_speed_mps": 0.0011495463049900365,
      "local_corner_max_m": [
        0.052484659987866666,
        0.20193390878791329,
        0.0365081862399777
      ],
      "local_corner_min_m": [
        -0.052444941053086946,
        0.1294380871653602,
        -0.036155321942201224
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759259055428269,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392434464537216,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02526920525413788,
      "step_index": 2149,
      "timestamp_seconds": 8.596000408288091,
      "trace_row": 2149,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09716851347441192,
      "vertical_lower_margin_m": 0.10767269185185885,
      "vertical_upper_margin_m": -0.09716851347441192
    },
    {
      "actual_left_finger_qpos_m": [
        0.0229440126568079,
        0.022298257797956467
      ],
      "angular_speed_rps": 0.003276981117137905,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.1275049525454337e-05,
        0.16568168320631815,
        0.00017787003734281992
      ],
      "can_pose": [
        -0.29289188981056213,
        -0.15262427926063538,
        0.9423949718475342,
        0.0008295465377159417,
        0.7006359100341797,
        0.04778937250375748,
        0.711916446685791
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010973277830206815,
      "can_relative_translation_from_partial_start_m": [
        0.0007507354021072388,
        -0.0007202029228210449,
        -0.0013352930545806885
      ],
      "can_to_box_relative_orientation_rad": 1.503234423468079,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.018960854038596153,
        0.018960854038596153
      ],
      "left_finger_qf_audit_only": [
        6.818050384521484,
        -6.818083763122559
      ],
      "left_finger_qvel_mps": [
        -0.0028033931739628315,
        0.002203491749241948
      ],
      "linear_speed_mps": 0.001152367784777642,
      "local_corner_max_m": [
        0.05248635610615865,
        0.2019298132879801,
        0.03651035438902428
      ],
      "local_corner_min_m": [
        -0.05244380600710774,
        0.1294335531246562,
        -0.03615461431433864
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07759115266582811,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392363701750957,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025267509135845898,
      "step_index": 2150,
      "timestamp_seconds": 8.600000408478081,
      "trace_row": 2150,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09716441797447874,
      "vertical_lower_margin_m": 0.10766815781115485,
      "vertical_upper_margin_m": -0.09716441797447874
    },
    {
      "actual_left_finger_qpos_m": [
        0.022940238937735558,
        0.022303059697151184
      ],
      "angular_speed_rps": 0.0037611971526772636,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.272257753843654e-05,
        0.16567745620769647,
        0.00017917875279788165
      ],
      "can_pose": [
        -0.2928912341594696,
        -0.15262287855148315,
        0.9423906803131104,
        0.0008249966194853187,
        0.7006338238716125,
        0.04779469594359398,
        0.7119182348251343
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010983261797120477,
      "can_relative_translation_from_partial_start_m": [
        0.0007521361112594604,
        -0.000724494457244873,
        -0.0013346374034881592
      ],
      "can_to_box_relative_orientation_rad": 1.50323385981842,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.019123556092381477,
        0.019123556092381477
      ],
      "left_finger_qf_audit_only": [
        6.817995548248291,
        -6.818037033081055
      ],
      "left_finger_qvel_mps": [
        -0.002634013071656227,
        0.0020641563460230827
      ],
      "linear_speed_mps": 0.0011404256392459596,
      "local_corner_max_m": [
        0.052488241428357646,
        0.20192580842037222,
        0.03651248752989783
      ],
      "local_corner_min_m": [
        -0.052442796273280745,
        0.12942910399502072,
        -0.03615413002430207
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758984395037305,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.113923152727473,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0252656238136469,
      "step_index": 2151,
      "timestamp_seconds": 8.604000408668071,
      "trace_row": 2151,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09716041310687086,
      "vertical_lower_margin_m": 0.10766370868151937,
      "vertical_upper_margin_m": -0.09716041310687086
    },
    {
      "actual_left_finger_qpos_m": [
        0.022936593741178513,
        0.0223077479749918
      ],
      "angular_speed_rps": 0.0030488994566807807,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.404385081344884e-05,
        0.1656735977516136,
        0.0001807416513224802
      ],
      "can_pose": [
        -0.29289010167121887,
        -0.1526215821504593,
        0.9423868656158447,
        0.000821263762190938,
        0.7006309628486633,
        0.0477975569665432,
        0.7119208574295044
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010989285089210876,
      "can_relative_translation_from_partial_start_m": [
        0.0007534325122833252,
        -0.000728309154510498,
        -0.0013335049152374268
      ],
      "can_to_box_relative_orientation_rad": 1.5032354777320238,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.0192862581461668,
        0.0192862581461668
      ],
      "left_finger_qf_audit_only": [
        6.817947864532471,
        -6.817982196807861
      ],
      "left_finger_qvel_mps": [
        -0.0025192932225763798,
        0.001975202700123191
      ],
      "linear_speed_mps": 0.0010462760993532685,
      "local_corner_max_m": [
        0.052489797682843176,
        0.2019221483368071,
        0.03651472407415185
      ],
      "local_corner_min_m": [
        -0.05244170998121628,
        0.12942504716642012,
        -0.03615324077150689
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758828105184845,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392226347467782,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02526406755916137,
      "step_index": 2152,
      "timestamp_seconds": 8.60800040885806,
      "trace_row": 2152,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09715675302330574,
      "vertical_lower_margin_m": 0.10765965185291876,
      "vertical_upper_margin_m": -0.09715675302330574
    },
    {
      "actual_left_finger_qpos_m": [
        0.02293306775391102,
        0.02231224626302719
      ],
      "angular_speed_rps": 0.0021554977140762015,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.5294175522549978e-05,
        0.16566955023176178,
        0.00018166793144519522
      ],
      "can_pose": [
        -0.29288923740386963,
        -0.1526203155517578,
        0.9423831105232239,
        0.0008185077458620071,
        0.7006289958953857,
        0.047795820981264114,
        0.7119228839874268
      ],
      "can_relative_orientation_from_partial_start_rad": 0.010990953352227611,
      "can_relative_translation_from_partial_start_m": [
        0.0007546991109848022,
        -0.0007320642471313477,
        -0.0013326406478881836
      ],
      "can_to_box_relative_orientation_rad": 1.503241924956745,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.019448960199952126,
        0.019448960199952126
      ],
      "left_finger_qf_audit_only": [
        6.817902088165283,
        -6.817933559417725
      ],
      "left_finger_qvel_mps": [
        -0.002605415415018797,
        0.001993159530684352
      ],
      "linear_speed_mps": 0.0010140250659457025,
      "local_corner_max_m": [
        0.05249090357255576,
        0.20191800503569313,
        0.036515885555191196
      ],
      "local_corner_min_m": [
        -0.05244031522151066,
        0.12942109542783042,
        -0.036152549692300806
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758735477172574,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392157239547174,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02526296166944879,
      "step_index": 2153,
      "timestamp_seconds": 8.61200040904805,
      "trace_row": 2153,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09715260972219177,
      "vertical_lower_margin_m": 0.10765570011432907,
      "vertical_upper_margin_m": -0.09715260972219177
    },
    {
      "actual_left_finger_qpos_m": [
        0.022929728031158447,
        0.022316552698612213
      ],
      "angular_speed_rps": 0.003391550828490869,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.6643025518746644e-05,
        0.1656657718637573,
        0.00018274027158871053
      ],
      "can_pose": [
        -0.2928886413574219,
        -0.15261900424957275,
        0.9423792362213135,
        0.0008154420647770166,
        0.7006257772445679,
        0.04780007153749466,
        0.711925745010376
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01099656859774172,
      "can_relative_translation_from_partial_start_m": [
        0.0007560104131698608,
        -0.000735938549041748,
        -0.0013320446014404297
      ],
      "can_to_box_relative_orientation_rad": 1.503240675828675,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.01961166225373745,
        0.01961166225373745
      ],
      "left_finger_qf_audit_only": [
        6.817851543426514,
        -6.817883491516113
      ],
      "left_finger_qvel_mps": [
        -0.0024745669215917587,
        0.0018697148188948631
      ],
      "linear_speed_mps": 0.0010333500876507139,
      "local_corner_max_m": [
        0.052492602577387054,
        0.20191458308053567,
        0.03651770710045099
      ],
      "local_corner_min_m": [
        -0.05243931652634959,
        0.12941696064697894,
        -0.03615222655727357
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758628243158222,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139212492604445,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025261262664617493,
      "step_index": 2154,
      "timestamp_seconds": 8.61600040923804,
      "trace_row": 2154,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09714918776703431,
      "vertical_lower_margin_m": 0.10765156533347758,
      "vertical_upper_margin_m": -0.09714918776703431
    },
    {
      "actual_left_finger_qpos_m": [
        0.022926580160856247,
        0.022320782765746117
      ],
      "angular_speed_rps": 0.0032886523655235294,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.8072484228675032e-05,
        0.16566204048453181,
        0.00018376276472453767
      ],
      "can_pose": [
        -0.2928880751132965,
        -0.15261761844158173,
        0.9423753023147583,
        0.0008133352966979146,
        0.7006229162216187,
        0.047804977744817734,
        0.7119283080101013
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011001309519662284,
      "can_relative_translation_from_partial_start_m": [
        0.0007573962211608887,
        -0.0007398724555969238,
        -0.0013314783573150635
      ],
      "can_to_box_relative_orientation_rad": 1.5032371258545745,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.019774364307522774,
        0.019774364307522774
      ],
      "left_finger_qf_audit_only": [
        6.817800045013428,
        -6.81783390045166
      ],
      "left_finger_qvel_mps": [
        -0.002391245448961854,
        0.0018544234335422516
      ],
      "linear_speed_mps": 0.0010522807164489675,
      "local_corner_max_m": [
        0.05249443647928498,
        0.20191127937213826,
        0.03651943166652477
      ],
      "local_corner_min_m": [
        -0.05243829151082763,
        0.12941280159692536,
        -0.036151906137075696
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0775852599384464,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392092884024663,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02525942876271957,
      "step_index": 2155,
      "timestamp_seconds": 8.62000040942803,
      "trace_row": 2155,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0971458840586369,
      "vertical_lower_margin_m": 0.10764740628342401,
      "vertical_upper_margin_m": -0.0971458840586369
    },
    {
      "actual_left_finger_qpos_m": [
        0.022923557087779045,
        0.022324716672301292
      ],
      "angular_speed_rps": 0.0023507203710525283,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.9068689825745286e-05,
        0.16565825057110006,
        0.00018469443494423254
      ],
      "can_pose": [
        -0.29288747906684875,
        -0.15261664986610413,
        0.9423714280128479,
        0.0008113065850920975,
        0.7006207704544067,
        0.047808099538087845,
        0.7119302153587341
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01100525438003602,
      "can_relative_translation_from_partial_start_m": [
        0.0007583647966384888,
        -0.0007437467575073242,
        -0.0013308823108673096
      ],
      "can_to_box_relative_orientation_rad": 1.503235878728363,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.019937066361308098,
        0.019937066361308098
      ],
      "left_finger_qf_audit_only": [
        6.817753314971924,
        -6.817787170410156
      ],
      "left_finger_qvel_mps": [
        -0.0026898374781012535,
        0.002122932579368353
      ],
      "linear_speed_mps": 0.0010094436452775376,
      "local_corner_max_m": [
        0.05249568986817199,
        0.2019077459344406,
        0.03652088121026764
      ],
      "local_corner_min_m": [
        -0.0524375524885205,
        0.12940875520775952,
        -0.03615149234037918
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0775843282682267,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392051504355011,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025258175373832556,
      "step_index": 2156,
      "timestamp_seconds": 8.62400040961802,
      "trace_row": 2156,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09714235062093925,
      "vertical_lower_margin_m": 0.10764335989425816,
      "vertical_upper_margin_m": -0.09714235062093925
    },
    {
      "actual_left_finger_qpos_m": [
        0.022920804098248482,
        0.02232849784195423
      ],
      "angular_speed_rps": 0.003482933476059406,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.0556268679760024e-05,
        0.1656548271558732,
        0.00018582372422593085
      ],
      "can_pose": [
        -0.29288673400878906,
        -0.15261518955230713,
        0.9423679709434509,
        0.0008084142464213073,
        0.700616717338562,
        0.047811202704906464,
        0.711933970451355
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011008964435090352,
      "can_relative_translation_from_partial_start_m": [
        0.0007598251104354858,
        -0.0007472038269042969,
        -0.0013301372528076172
      ],
      "can_to_box_relative_orientation_rad": 1.5032359629885792,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.020099768415093422,
        0.020099768415093422
      ],
      "left_finger_qf_audit_only": [
        6.817676544189453,
        -6.817723274230957
      ],
      "left_finger_qvel_mps": [
        -0.0023526446893811226,
        0.0018504296895116568
      ],
      "linear_speed_mps": 0.0009565221940339158,
      "local_corner_max_m": [
        0.05249743291742692,
        0.20190470097582003,
        0.036522744910605254
      ],
      "local_corner_min_m": [
        -0.0524363203800674,
        0.1294049533359264,
        -0.03615109746215339
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.077583198978945,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392012016532432,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025256432324577624,
      "step_index": 2157,
      "timestamp_seconds": 8.62800040980801,
      "trace_row": 2157,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09713930566231867,
      "vertical_lower_margin_m": 0.10763955802242503,
      "vertical_upper_margin_m": -0.09713930566231867
    },
    {
      "actual_left_finger_qpos_m": [
        0.022918175905942917,
        0.022332098335027695
      ],
      "angular_speed_rps": 0.0028480445789696735,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.1851188375869866e-05,
        0.1656513953088523,
        0.00018648012464511643
      ],
      "can_pose": [
        -0.292886346578598,
        -0.15261389315128326,
        0.9423648118972778,
        0.0008042034460231662,
        0.7006139755249023,
        0.04781114682555199,
        0.7119366526603699
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011013764334006294,
      "can_relative_translation_from_partial_start_m": [
        0.0007611215114593506,
        -0.0007503628730773926,
        -0.0013297498226165771
      ],
      "can_to_box_relative_orientation_rad": 1.503242261496781,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.020262470468878746,
        0.020262470468878746
      ],
      "left_finger_qf_audit_only": [
        6.817622184753418,
        -6.817658424377441
      ],
      "left_finger_qvel_mps": [
        -0.0025581810623407364,
        0.0019843080081045628
      ],
      "linear_speed_mps": 0.0008591539941068617,
      "local_corner_max_m": [
        0.05249872160676669,
        0.20190125219904653,
        0.03652390688603746
      ],
      "local_corner_min_m": [
        -0.05243501923001498,
        0.1294015384186581,
        -0.03615094663674723
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758254257852581,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11391996933991816,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025255143635237856,
      "step_index": 2158,
      "timestamp_seconds": 8.632000409998,
      "trace_row": 2158,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09713585688554517,
      "vertical_lower_margin_m": 0.10763614310515673,
      "vertical_upper_margin_m": -0.09713585688554517
    },
    {
      "actual_left_finger_qpos_m": [
        0.02291569672524929,
        0.022335538640618324
      ],
      "angular_speed_rps": 0.004801805623026497,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.3327324609311315e-05,
        0.16564793826727353,
        0.00018751945058931296
      ],
      "can_pose": [
        -0.2928858697414398,
        -0.15261243283748627,
        0.9423616528511047,
        0.0007974767358973622,
        0.7006092071533203,
        0.04781307652592659,
        0.7119411826133728
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011022643692529246,
      "can_relative_translation_from_partial_start_m": [
        0.0007625818252563477,
        -0.0007535219192504883,
        -0.001329272985458374
      ],
      "can_to_box_relative_orientation_rad": 1.5032495741606182,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.02042517252266407,
        0.02042517252266407
      ],
      "left_finger_qf_audit_only": [
        6.817554473876953,
        -6.817600250244141
      ],
      "left_finger_qvel_mps": [
        -0.0022588393185287714,
        0.001813104609027505
      ],
      "linear_speed_mps": 0.0008781892454330336,
      "local_corner_max_m": [
        0.052500354622732254,
        0.20189792402899487,
        0.03652591733826693
      ],
      "local_corner_min_m": [
        -0.0524336999735136,
        0.1293979525055522,
        -0.03615087843708831
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758150325258162,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11391990114025924,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025253510619272293,
      "step_index": 2159,
      "timestamp_seconds": 8.63600041018799,
      "trace_row": 2159,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09713252871549351,
      "vertical_lower_margin_m": 0.10763255719205084,
      "vertical_upper_margin_m": -0.09713252871549351
    },
    {
      "actual_left_finger_qpos_m": [
        0.022913428023457527,
        0.02233888767659664
      ],
      "angular_speed_rps": 0.005086786696138303,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.478875754930888e-05,
        0.16564492548365584,
        0.00018837491818080032
      ],
      "can_pose": [
        -0.29288578033447266,
        -0.15261100232601166,
        0.9423589110374451,
        0.0007894899463281035,
        0.7006054520606995,
        0.04781671613454819,
        0.7119446992874146
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011035926300850258,
      "can_relative_translation_from_partial_start_m": [
        0.000764012336730957,
        -0.0007562637329101562,
        -0.001329183578491211
      ],
      "can_to_box_relative_orientation_rad": 1.5032563764586122,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.020587874576449394,
        0.020587874576449394
      ],
      "left_finger_qf_audit_only": [
        6.817489147186279,
        -6.817528247833252
      ],
      "left_finger_qvel_mps": [
        -0.002198451431468129,
        0.0017524550203233957
      ],
      "linear_speed_mps": 0.0007734620999048174,
      "local_corner_max_m": [
        0.05250211330302912,
        0.20189496854770184,
        0.03652785510180251
      ],
      "local_corner_min_m": [
        -0.0524325357879305,
        0.12939488241960984,
        -0.03615110526544091
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758064778499013,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392012796861184,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025251751938975428,
      "step_index": 2160,
      "timestamp_seconds": 8.64000041037798,
      "trace_row": 2160,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09712957323420048,
      "vertical_lower_margin_m": 0.10762948710610848,
      "vertical_upper_margin_m": -0.09712957323420048
    },
    {
      "actual_left_finger_qpos_m": [
        0.02291124500334263,
        0.02234191820025444
      ],
      "angular_speed_rps": 0.00696106839519043,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.6210775683581664e-05,
        0.1656415377565369,
        0.00018909124535287924
      ],
      "can_pose": [
        -0.29288601875305176,
        -0.15260960161685944,
        0.9423561096191406,
        0.0007776792626827955,
        0.7006004452705383,
        0.04781937971711159,
        0.7119494080543518
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011054083403733697,
      "can_relative_translation_from_partial_start_m": [
        0.0007654130458831787,
        -0.0007590651512145996,
        -0.0013294219970703125
      ],
      "can_to_box_relative_orientation_rad": 1.503270128999677,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.02075057663023472,
        0.02075057663023472
      ],
      "left_finger_qf_audit_only": [
        6.817440032958984,
        -6.817476272583008
      ],
      "left_finger_qvel_mps": [
        -0.0025789239443838596,
        0.0020363242365419865
      ],
      "linear_speed_mps": 0.0007852855025067124,
      "local_corner_max_m": [
        0.05250375056857606,
        0.2018914471767178,
        0.03652994419976119
      ],
      "local_corner_min_m": [
        -0.05243132901720887,
        0.12939162833635598,
        -0.03615176170905543
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757993145781805,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392078441222636,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025250114673428484,
      "step_index": 2161,
      "timestamp_seconds": 8.644000410567969,
      "trace_row": 2161,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09712605186321645,
      "vertical_lower_margin_m": 0.10762623302285462,
      "vertical_upper_margin_m": -0.09712605186321645
    },
    {
      "actual_left_finger_qpos_m": [
        0.022909240797162056,
        0.02234496735036373
      ],
      "angular_speed_rps": 0.006240491785901734,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.778523065547934e-05,
        0.16563848672125925,
        0.00019009583846180123
      ],
      "can_pose": [
        -0.29288575053215027,
        -0.15260803699493408,
        0.9423536062240601,
        0.0007677641697227955,
        0.7005950808525085,
        0.047820720821619034,
        0.7119545936584473
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011067619561735369,
      "can_relative_translation_from_partial_start_m": [
        0.0007669776678085327,
        -0.000761568546295166,
        -0.0013291537761688232
      ],
      "can_to_box_relative_orientation_rad": 1.503282926052289,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.020913278684020042,
        0.020913278684020042
      ],
      "left_finger_qf_audit_only": [
        6.817355155944824,
        -6.817409038543701
      ],
      "left_finger_qvel_mps": [
        -0.002204553922638297,
        0.0018302369862794876
      ],
      "linear_speed_mps": 0.0007410706071278252,
      "local_corner_max_m": [
        0.05250543172835542,
        0.20188834211626627,
        0.03653214330854837
      ],
      "local_corner_min_m": [
        -0.052429861267044464,
        0.12938863132625222,
        -0.03615195163162477
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757892686470913,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139209743347957,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025248433513649124,
      "step_index": 2162,
      "timestamp_seconds": 8.648000410757959,
      "trace_row": 2162,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09712294680276491,
      "vertical_lower_margin_m": 0.10762323601275087,
      "vertical_upper_margin_m": -0.09712294680276491
    },
    {
      "actual_left_finger_qpos_m": [
        0.02290736697614193,
        0.022347919642925262
      ],
      "angular_speed_rps": 0.010765521880347151,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.948736565964617e-05,
        0.16563509537202925,
        0.000190647805777322
      ],
      "can_pose": [
        -0.2928863763809204,
        -0.1526063084602356,
        0.9423516988754272,
        0.0007476368336938322,
        0.7005900144577026,
        0.04781828820705414,
        0.7119597792625427
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011096435885254408,
      "can_relative_translation_from_partial_start_m": [
        0.000768706202507019,
        -0.0007634758949279785,
        -0.0013297796249389648
      ],
      "can_to_box_relative_orientation_rad": 1.5033158129136313,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.021075980737805367,
        0.021075980737805367
      ],
      "left_finger_qf_audit_only": [
        6.817286968231201,
        -6.817326545715332
      ],
      "left_finger_qvel_mps": [
        -0.0022442934568971395,
        0.001738951075822115
      ],
      "linear_speed_mps": 0.0006622639686816838,
      "local_corner_max_m": [
        0.05250692399161003,
        0.20188398831968524,
        0.03653429342362752
      ],
      "local_corner_min_m": [
        -0.05242794926029071,
        0.12938620242437326,
        -0.03615299781207287
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757837489739361,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139220205152438,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02524694125039452,
      "step_index": 2163,
      "timestamp_seconds": 8.652000410947949,
      "trace_row": 2163,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09711859300618388,
      "vertical_lower_margin_m": 0.10762080711087191,
      "vertical_upper_margin_m": -0.09711859300618388
    },
    {
      "actual_left_finger_qpos_m": [
        0.022905532270669937,
        0.022350676357746124
      ],
      "angular_speed_rps": 0.005184639805640529,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.989345988442139e-05,
        0.16563291968301586,
        0.00019085928978385125
      ],
      "can_pose": [
        -0.2928857207298279,
        -0.15260592103004456,
        0.942348837852478,
        0.0007557359640486538,
        0.7005855441093445,
        0.04782016575336456,
        0.7119640707969666
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011079710446052129,
      "can_relative_translation_from_partial_start_m": [
        0.0007690936326980591,
        -0.0007663369178771973,
        -0.0013291239738464355
      ],
      "can_to_box_relative_orientation_rad": 1.5033015059239792,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.02123868279159069,
        0.02123868279159069
      ],
      "left_finger_qf_audit_only": [
        6.817221641540527,
        -6.817257881164551
      ],
      "left_finger_qvel_mps": [
        -0.0023226458579301834,
        0.0017404456157237291
      ],
      "linear_speed_mps": 0.0007401618062689552,
      "local_corner_max_m": [
        0.05250748908155428,
        0.20188286943293765,
        0.036534474736064415
      ],
      "local_corner_min_m": [
        -0.05242770216178544,
        0.12938296993309406,
        -0.03615275615649671
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757816341338708,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392177885966764,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025246376160450265,
      "step_index": 2164,
      "timestamp_seconds": 8.656000411137938,
      "trace_row": 2164,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09711747411943629,
      "vertical_lower_margin_m": 0.1076175746195927,
      "vertical_upper_margin_m": -0.09711747411943629
    },
    {
      "actual_left_finger_qpos_m": [
        0.022903895005583763,
        0.02235329896211624
      ],
      "angular_speed_rps": 0.03852527562532887,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        4.033047867949002e-05,
        0.16562913641162913,
        0.00019294956282323028
      ],
      "can_pose": [
        -0.29288941621780396,
        -0.1526055485010147,
        0.9423495531082153,
        0.0006793689681217074,
        0.7005888223648071,
        0.04782913625240326,
        0.7119603753089905
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0112232127496839,
      "can_relative_translation_from_partial_start_m": [
        0.0007694661617279053,
        -0.0007656216621398926,
        -0.0013328194618225098
      ],
      "can_to_box_relative_orientation_rad": 1.5034008990525347,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.021401384845376015,
        0.021401384845376015
      ],
      "left_finger_qf_audit_only": [
        6.81715726852417,
        -6.817200660705566
      ],
      "left_finger_qvel_mps": [
        -0.002222253940999508,
        0.001676567830145359
      ],
      "linear_speed_mps": 0.0009456148353730816,
      "local_corner_max_m": [
        0.05250863165447722,
        0.20187438394630697,
        0.036541891103192004
      ],
      "local_corner_min_m": [
        -0.05242797069711824,
        0.1293838888769513,
        -0.03615599197754554
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0775760731403477,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11392501468071647,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025245233587527324,
      "step_index": 2165,
      "timestamp_seconds": 8.660000411327928,
      "trace_row": 2165,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0971089886328056,
      "vertical_lower_margin_m": 0.10761849356344994,
      "vertical_upper_margin_m": -0.0971089886328056
    },
    {
      "actual_left_finger_qpos_m": [
        0.022902388125658035,
        0.02235594391822815
      ],
      "angular_speed_rps": 0.08513614274955693,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.757861364558912e-05,
        0.16562620073235945,
        0.00018760452661525928
      ],
      "can_pose": [
        -0.2928849160671234,
        -0.15260834991931915,
        0.9423366785049438,
        0.0008302696514874697,
        0.700644850730896,
        0.04783090204000473,
        0.7119048833847046
      ],
      "can_relative_orientation_from_partial_start_rad": 0.011012194382447287,
      "can_relative_translation_from_partial_start_m": [
        0.0007666647434234619,
        -0.000778496265411377,
        -0.0013283193111419678
      ],
      "can_to_box_relative_orientation_rad": 1.5031764230648164,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.02156408689916134,
        0.02156408689916134
      ],
      "left_finger_qf_audit_only": [
        6.817089557647705,
        -6.817124843597412
      ],
      "left_finger_qvel_mps": [
        -0.002062402432784438,
        0.001691980054602027
      ],
      "linear_speed_mps": 0.0034807927585443904,
      "local_corner_max_m": [
        0.05250609072054724,
        0.20187598747148938,
        0.036521966816654594
      ],
      "local_corner_min_m": [
        -0.05243093349325606,
        0.12937641399322952,
        -0.036146757763424076
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758141817655567,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.113915780466595,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02524777452145731,
      "step_index": 2166,
      "timestamp_seconds": 8.664000411517918,
      "trace_row": 2166,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09711059215798802,
      "vertical_lower_margin_m": 0.10761101867972817,
      "vertical_upper_margin_m": -0.09711059215798802
    },
    {
      "actual_left_finger_qpos_m": [
        0.022900942713022232,
        0.022358005866408348
      ],
      "angular_speed_rps": 0.38954075451503445,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.4025270306093915e-05,
        0.16560670291532864,
        0.0001956761075733171
      ],
      "can_pose": [
        -0.2929266691207886,
        -0.15262186527252197,
        0.9423649907112122,
        0.00011855561751872301,
        0.7008705139160156,
        0.04783978313207626,
        0.7116825580596924
      ],
      "can_relative_orientation_from_partial_start_rad": 0.012476915580773492,
      "can_relative_translation_from_partial_start_m": [
        0.0007531493902206421,
        -0.0007501840591430664,
        -0.001370072364807129
      ],
      "can_to_box_relative_orientation_rad": 1.5042005348093874,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.021726788952946663,
        0.021726788952946663
      ],
      "left_finger_qf_audit_only": [
        6.817010402679443,
        -6.8170599937438965
      ],
      "left_finger_qvel_mps": [
        -0.0021559896413236856,
        0.0018044536700472236
      ],
      "linear_speed_mps": 0.01305651903082702,
      "local_corner_max_m": [
        0.05249291887005886,
        0.20178974897539248,
        0.03655816699085801
      ],
      "local_corner_min_m": [
        -0.05244486832944667,
        0.1294236568552648,
        -0.036166814775711376
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07757334659559761,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11393583747888231,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02526094637194569,
      "step_index": 2167,
      "timestamp_seconds": 8.668000411707908,
      "trace_row": 2167,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09702435366189112,
      "vertical_lower_margin_m": 0.10765826154176344,
      "vertical_upper_margin_m": -0.09702435366189112
    },
    {
      "actual_left_finger_qpos_m": [
        0.022899754345417023,
        0.022360488772392273
      ],
      "angular_speed_rps": 0.16563621071773404,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.84391157639452e-05,
        0.16557833279966938,
        0.00018040949856068522
      ],
      "can_pose": [
        -0.29295939207077026,
        -0.1526171863079071,
        0.9423574209213257,
        -0.00017316041339654475,
        0.7007612586021423,
        0.047812752425670624,
        0.7117919921875
      ],
      "can_relative_orientation_from_partial_start_rad": 0.012876655047733892,
      "can_relative_translation_from_partial_start_m": [
        0.0007578283548355103,
        -0.000757753849029541,
        -0.0014027953147888184
      ],
      "can_to_box_relative_orientation_rad": 1.5046668585980463,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.021889491006731987,
        0.021889491006731987
      ],
      "left_finger_qf_audit_only": [
        6.816925525665283,
        -6.816980838775635
      ],
      "left_finger_qvel_mps": [
        -0.0021747229620814323,
        0.0018330533057451248
      ],
      "linear_speed_mps": 0.00847786004489754,
      "local_corner_max_m": [
        0.05249492541056722,
        0.2017512874736629,
        0.036569602033397264
      ],
      "local_corner_min_m": [
        -0.05243804717903933,
        0.12940537812567587,
        -0.03620878303627589
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07758861320461025,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11397780573944682,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02525893983143733,
      "step_index": 2168,
      "timestamp_seconds": 8.672000411897898,
      "trace_row": 2168,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09698589216016153,
      "vertical_lower_margin_m": 0.10763998281217452,
      "vertical_upper_margin_m": -0.09698589216016153
    },
    {
      "actual_left_finger_qpos_m": [
        0.022898640483617783,
        0.02236284129321575
      ],
      "angular_speed_rps": 0.15103603624061998,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        2.7053346975364212e-05,
        0.16555401750334497,
        0.00016297413848692655
      ],
      "can_pose": [
        -0.2929765582084656,
        -0.1526174545288086,
        0.9423493146896362,
        -0.00030219194013625383,
        0.7005918622016907,
        0.04768906161189079,
        0.7119669318199158
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01289357052316767,
      "can_relative_translation_from_partial_start_m": [
        0.000757560133934021,
        -0.0007658600807189941,
        -0.0014199614524841309
      ],
      "can_to_box_relative_orientation_rad": 1.5050284753522556,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.02205219306051731,
        0.02205219306051731
      ],
      "left_finger_qf_audit_only": [
        6.81683874130249,
        -6.816890716552734
      ],
      "left_finger_qvel_mps": [
        -0.0019943458028137684,
        0.0014807006809860468
      ],
      "linear_speed_mps": 0.004746440665038729,
      "local_corner_max_m": [
        0.05248322315428813,
        0.20172734447709528,
        0.036567066049463526
      ],
      "local_corner_min_m": [
        -0.05242911646033743,
        0.12938069052959467,
        -0.03624111777248967
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.077606048564684,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1140101404756606,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025270642087716413,
      "step_index": 2169,
      "timestamp_seconds": 8.676000412087888,
      "trace_row": 2169,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09696194916359392,
      "vertical_lower_margin_m": 0.10761529521609331,
      "vertical_upper_margin_m": -0.09696194916359392
    },
    {
      "actual_left_finger_qpos_m": [
        0.022897684946656227,
        0.02236454375088215
      ],
      "angular_speed_rps": 0.16813434897634058,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        3.446740434445705e-05,
        0.1655231021815966,
        0.00014234652342354215
      ],
      "can_pose": [
        -0.2930040955543518,
        -0.15260906517505646,
        0.9423396587371826,
        -0.0005216755671426654,
        0.700431227684021,
        0.047580428421497345,
        0.7121321558952332
      ],
      "can_relative_orientation_from_partial_start_rad": 0.013121866196272279,
      "can_relative_translation_from_partial_start_m": [
        0.0007659494876861572,
        -0.0007755160331726074,
        -0.0014474987983703613
      ],
      "can_to_box_relative_orientation_rad": 1.5055018502185866,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022214895114302635,
        0.022214895114302635
      ],
      "left_finger_qf_audit_only": [
        6.816771507263184,
        -6.8168158531188965
      ],
      "left_finger_qvel_mps": [
        -0.001971564954146743,
        0.0015254926402121782
      ],
      "linear_speed_mps": 0.007590800373827245,
      "local_corner_max_m": [
        0.05248148875868,
        0.20169101058506844,
        0.036567494070497586
      ],
      "local_corner_min_m": [
        -0.052412553949991114,
        0.12935519377812477,
        -0.0362828010236505
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07762667617974739,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11405182372682143,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025272376483324546,
      "step_index": 2170,
      "timestamp_seconds": 8.680000412277877,
      "trace_row": 2170,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09692561527156708,
      "vertical_lower_margin_m": 0.10758979846462341,
      "vertical_upper_margin_m": -0.09692561527156708
    },
    {
      "actual_left_finger_qpos_m": [
        0.022896794602274895,
        0.02236620895564556
      ],
      "angular_speed_rps": 0.3228830245067671,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.9582260823658437e-05,
        0.16548019209489884,
        0.00011246534090997296
      ],
      "can_pose": [
        -0.2930396795272827,
        -0.15262219309806824,
        0.942328691482544,
        -0.0008249944658018649,
        0.7000565528869629,
        0.04738243296742439,
        0.7125135064125061
      ],
      "can_relative_orientation_from_partial_start_rad": 0.013392677773026948,
      "can_relative_translation_from_partial_start_m": [
        0.0007528215646743774,
        -0.0007864832878112793,
        -0.0014830827713012695
      ],
      "can_to_box_relative_orientation_rad": 1.506225417020395,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.02237759716808796,
        0.02237759716808796
      ],
      "left_finger_qf_audit_only": [
        6.816695213317871,
        -6.816745758056641
      ],
      "left_finger_qvel_mps": [
        -0.002027747454121709,
        0.0017092290800064802
      ],
      "linear_speed_mps": 0.009870543356302141,
      "local_corner_max_m": [
        0.052449942827961504,
        0.20165216097970806,
        0.03657659813039188
      ],
      "local_corner_min_m": [
        -0.05241077830631419,
        0.1293082232100896,
        -0.036351667448571934
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07765655736226096,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11412069015174287,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025303922414043042,
      "step_index": 2171,
      "timestamp_seconds": 8.684000412467867,
      "trace_row": 2171,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0968867656662067,
      "vertical_lower_margin_m": 0.10754282789658826,
      "vertical_upper_margin_m": -0.0968867656662067
    },
    {
      "actual_left_finger_qpos_m": [
        0.022896112874150276,
        0.022368377074599266
      ],
      "angular_speed_rps": 0.6021393025236829,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.0441512453551738e-05,
        0.16541610101608484,
        6.887925444226672e-05
      ],
      "can_pose": [
        -0.2930990159511566,
        -0.15262913703918457,
        0.9423137903213501,
        -0.0013545528054237366,
        0.699314296245575,
        0.04712827131152153,
        0.7132580280303955
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0141720041950496,
      "can_relative_translation_from_partial_start_m": [
        0.0007458776235580444,
        -0.000801384449005127,
        -0.001542419195175171
      ],
      "can_to_box_relative_orientation_rad": 1.5073676482171559,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8165998458862305,
        -6.816656589508057
      ],
      "left_finger_qvel_mps": [
        -0.001773596741259098,
        0.0015271364245563745
      ],
      "linear_speed_mps": 0.015392924026079995,
      "local_corner_max_m": [
        0.05241913409027163,
        0.20160871545606096,
        0.03661436200088647
      ],
      "local_corner_min_m": [
        -0.052398251065364554,
        0.12922348657610871,
        -0.036476603492001936
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07770014344872866,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11424562619517287,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025334731151732917,
      "step_index": 2172,
      "timestamp_seconds": 8.688000412657857,
      "trace_row": 2172,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0968433201425596,
      "vertical_lower_margin_m": 0.10745809126260736,
      "vertical_upper_margin_m": -0.0968433201425596
    },
    {
      "actual_left_finger_qpos_m": [
        0.02290407195687294,
        0.02238255739212036
      ],
      "angular_speed_rps": 0.23866566213275808,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        1.860104212203506e-05,
        0.16537088823401958,
        4.798764993524385e-05
      ],
      "can_pose": [
        -0.293114572763443,
        -0.1526188850402832,
        0.9422951936721802,
        -0.0015277366619557142,
        0.6990547180175781,
        0.04688820615410805,
        0.7135279178619385
      ],
      "can_relative_orientation_from_partial_start_rad": 0.014457370236040976,
      "can_relative_translation_from_partial_start_m": [
        0.0007561296224594116,
        -0.0008199810981750488,
        -0.0015579760074615479
      ],
      "can_to_box_relative_orientation_rad": 1.5079563810026992,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.816526889801025,
        -6.8165740966796875
      ],
      "left_finger_qvel_mps": [
        -0.0009104080963879824,
        0.0038022140506654978
      ],
      "linear_speed_mps": 0.006581000990110362,
      "local_corner_max_m": [
        0.052407168641879165,
        0.2015624369525909,
        0.036611364394518675
      ],
      "local_corner_min_m": [
        -0.052369966557635095,
        0.12917933951544824,
        -0.03651538909464819
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07772103505323569,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11428441179781912,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025346696600125382,
      "step_index": 2173,
      "timestamp_seconds": 8.692000412847847,
      "trace_row": 2173,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09679704163908955,
      "vertical_lower_margin_m": 0.10741394420194689,
      "vertical_upper_margin_m": -0.09679704163908955
    },
    {
      "actual_left_finger_qpos_m": [
        0.022902969270944595,
        0.022387929260730743
      ],
      "angular_speed_rps": 0.5587293214029977,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0001075042169864926,
        0.16532343508187597,
        1.6830616622387495e-05
      ],
      "can_pose": [
        -0.2931307554244995,
        -0.15274176001548767,
        0.9422823190689087,
        -0.001717054983600974,
        0.6983258724212646,
        0.04651632532477379,
        0.7142650485038757
      ],
      "can_relative_orientation_from_partial_start_rad": 0.015005594743258039,
      "can_relative_translation_from_partial_start_m": [
        0.0006332546472549438,
        -0.0008328557014465332,
        -0.0015741586685180664
      ],
      "can_to_box_relative_orientation_rad": 1.5087637847668596,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8164591789245605,
        -6.816493034362793
      ],
      "left_finger_qvel_mps": [
        -0.0013622306287288666,
        0.001739585306495428
      ],
      "linear_speed_mps": 0.031150734326101985,
      "local_corner_max_m": [
        0.052249833021495884,
        0.20154895504939885,
        0.036630359258917
      ],
      "local_corner_min_m": [
        -0.05246484145546887,
        0.1290979151143531,
        -0.036596698025672225
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07775219208654854,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11436572072884316,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025504032220508663,
      "step_index": 2174,
      "timestamp_seconds": 8.696000413037837,
      "trace_row": 2174,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09678355973589749,
      "vertical_lower_margin_m": 0.10733251980085173,
      "vertical_upper_margin_m": -0.09678355973589749
    },
    {
      "actual_left_finger_qpos_m": [
        0.022901801392436028,
        0.022389806807041168
      ],
      "angular_speed_rps": 0.7151479672432152,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00020444932150248674,
        0.16520121511157992,
        -8.061873387726903e-05
      ],
      "can_pose": [
        -0.2932373881340027,
        -0.15283559262752533,
        0.9422186613082886,
        -0.002273997524753213,
        0.6974339485168457,
        0.04614069312810898,
        0.7151588797569275
      ],
      "can_relative_orientation_from_partial_start_rad": 0.01669350843332223,
      "can_relative_translation_from_partial_start_m": [
        0.0005394220352172852,
        -0.0008965134620666504,
        -0.0016807913780212402
      ],
      "can_to_box_relative_orientation_rad": 1.510122433611135,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.816383361816406,
        -6.816432952880859
      ],
      "left_finger_qvel_mps": [
        -0.0016771727241575718,
        0.0013834228739142418
      ],
      "linear_speed_mps": 0.038912885079596726,
      "local_corner_max_m": [
        0.05212069399680502,
        0.2014517227403796,
        0.036620566172136104
      ],
      "local_corner_min_m": [
        -0.05252959263981,
        0.12895070748278026,
        -0.03678180363989064
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0778496414370482,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11455082634306157,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025633171245199524,
      "step_index": 2175,
      "timestamp_seconds": 8.700000413227826,
      "trace_row": 2175,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09668632742687823,
      "vertical_lower_margin_m": 0.1071853121692789,
      "vertical_upper_margin_m": -0.09668632742687823
    },
    {
      "actual_left_finger_qpos_m": [
        0.02290036343038082,
        0.022391127422451973
      ],
      "angular_speed_rps": 1.0165417603364308,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0002890271627233598,
        0.16501774392482949,
        -0.00022645596224035724
      ],
      "can_pose": [
        -0.29340922832489014,
        -0.15291710197925568,
        0.9421125650405884,
        -0.0031192072201520205,
        0.6961509585380554,
        0.045743994414806366,
        0.7164299488067627
      ],
      "can_relative_orientation_from_partial_start_rad": 0.019669686253396153,
      "can_relative_translation_from_partial_start_m": [
        0.0004579126834869385,
        -0.0010026097297668457,
        -0.0018526315689086914
      ],
      "can_to_box_relative_orientation_rad": 1.5119508514206321,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.816298484802246,
        -6.8163604736328125
      ],
      "left_finger_qvel_mps": [
        -0.0017453274922445416,
        0.0014527342282235622
      ],
      "linear_speed_mps": 0.054445637530770356,
      "local_corner_max_m": [
        0.05200126651034853,
        0.20130935570881459,
        0.03661257142531682
      ],
      "local_corner_min_m": [
        -0.05257932083579525,
        0.12872613214084438,
        -0.037065483349797534
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07795710759527223,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11483450605296847,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02566681392220034,
      "step_index": 2176,
      "timestamp_seconds": 8.704000413417816,
      "trace_row": 2176,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09654396039531322,
      "vertical_lower_margin_m": 0.10696073682734303,
      "vertical_upper_margin_m": -0.09654396039531322
    },
    {
      "actual_left_finger_qpos_m": [
        0.022898856550455093,
        0.02239255979657173
      ],
      "angular_speed_rps": 1.336406497465859,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0003698027951824223,
        0.16477895209378268,
        -0.0004219114239895627
      ],
      "can_pose": [
        -0.2936457395553589,
        -0.15299496054649353,
        0.9419681429862976,
        -0.004227318335324526,
        0.6944412589073181,
        0.04532412067055702,
        0.7181082367897034
      ],
      "can_relative_orientation_from_partial_start_rad": 0.024083515155128066,
      "can_relative_translation_from_partial_start_m": [
        0.00038005411624908447,
        -0.0011470317840576172,
        -0.0020891427993774414
      ],
      "can_to_box_relative_orientation_rad": 1.5142226355774253,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.816211223602295,
        -6.816272258758545
      ],
      "left_finger_qvel_mps": [
        -0.0015781112015247345,
        0.0012393114157021046
      ],
      "linear_speed_mps": 0.07196233412553597,
      "local_corner_max_m": [
        0.051882413447081444,
        0.20113207593511018,
        0.03660589220618354
      ],
      "local_corner_min_m": [
        -0.05262201903744629,
        0.1284258282524552,
        -0.03744971505416267
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07780906587283964,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11483686950301275,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025624115720549304,
      "step_index": 2177,
      "timestamp_seconds": 8.708000413607806,
      "trace_row": 2177,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09636668062160882,
      "vertical_lower_margin_m": 0.10666043293895383,
      "vertical_upper_margin_m": -0.09636668062160882
    },
    {
      "actual_left_finger_qpos_m": [
        0.02289775386452675,
        0.022394303232431412
      ],
      "angular_speed_rps": 1.656557421159479,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00044957482643348534,
        0.1645093620969783,
        -0.0006782447748239218
      ],
      "can_pose": [
        -0.29393863677978516,
        -0.15307210385799408,
        0.9417864084243774,
        -0.005283372476696968,
        0.6922093629837036,
        0.0449126735329628,
        0.7202786803245544
      ],
      "can_relative_orientation_from_partial_start_rad": 0.02968690994138158,
      "can_relative_translation_from_partial_start_m": [
        0.00030291080474853516,
        -0.0013287663459777832,
        -0.002382040023803711
      ],
      "can_to_box_relative_orientation_rad": 1.5164474388079314,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.816136360168457,
        -6.816181659698486
      ],
      "left_finger_qvel_mps": [
        -0.0015595329459756613,
        0.0015391615452244878
      ],
      "linear_speed_mps": 0.08830604230810697,
      "local_corner_max_m": [
        0.05176421267764886,
        0.20097457924571416,
        0.036577867734876535
      ],
      "local_corner_min_m": [
        -0.05266336233051583,
        0.12804414494824246,
        -0.03793435728452438
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07755273252200529,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11480884503170574,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025582772427479764,
      "step_index": 2178,
      "timestamp_seconds": 8.712000413797796,
      "trace_row": 2178,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0962091839322128,
      "vertical_lower_margin_m": 0.1062787496347411,
      "vertical_upper_margin_m": -0.0962091839322128
    },
    {
      "actual_left_finger_qpos_m": [
        0.02289600856602192,
        0.02239542454481125
      ],
      "angular_speed_rps": 1.8718112045280606,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005367269287648302,
        0.16416414468173524,
        -0.000977449622651172
      ],
      "can_pose": [
        -0.29426658153533936,
        -0.15315687656402588,
        0.941518247127533,
        -0.006220197770744562,
        0.6896156072616577,
        0.04451780393719673,
        0.722779393196106
      ],
      "can_relative_orientation_from_partial_start_rad": 0.03621397079542174,
      "can_relative_translation_from_partial_start_m": [
        0.00021813809871673584,
        -0.0015969276428222656,
        -0.00270998477935791
      ],
      "can_to_box_relative_orientation_rad": 1.518518274448967,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.816047191619873,
        -6.816107273101807
      ],
      "left_finger_qvel_mps": [
        -0.0016807755455374718,
        0.0013384700287133455
      ],
      "linear_speed_mps": 0.10800597141433961,
      "local_corner_max_m": [
        0.05163917549311914,
        0.20078107865990635,
        0.0365283820087432
      ],
      "local_corner_min_m": [
        -0.0527126293506488,
        0.12754721070356412,
        -0.03848328125404554
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07725352767417804,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1147593593055724,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025533505407346793,
      "step_index": 2179,
      "timestamp_seconds": 8.716000413987786,
      "trace_row": 2179,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09601568334640499,
      "vertical_lower_margin_m": 0.10578181539006276,
      "vertical_upper_margin_m": -0.09601568334640499
    },
    {
      "actual_left_finger_qpos_m": [
        0.022904131561517715,
        0.02240907959640026
      ],
      "angular_speed_rps": 2.2647536859321775,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0005458977832688006,
        0.16393296450061112,
        -0.0011883054727849784
      ],
      "can_pose": [
        -0.29443109035491943,
        -0.15316271781921387,
        0.941289484500885,
        -0.006079815328121185,
        0.6863567233085632,
        0.0441385880112648,
        0.7258991003036499
      ],
      "can_relative_orientation_from_partial_start_rad": 0.04332312004303586,
      "can_relative_translation_from_partial_start_m": [
        0.00021229684352874756,
        -0.0018256902694702148,
        -0.0028744935989379883
      ],
      "can_to_box_relative_orientation_rad": 1.5190672922272719,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8159685134887695,
        -6.816020965576172
      ],
      "left_finger_qvel_mps": [
        -0.0032386912498623133,
        0.0010126926936209202
      ],
      "linear_speed_mps": 0.07045814528288374,
      "local_corner_max_m": [
        0.05159588895328254,
        0.20082840362451215,
        0.03654894605319392
      ],
      "local_corner_min_m": [
        -0.052687684519820144,
        0.1270375253767101,
        -0.03892555699876388
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07704267182404423,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11477992335002313,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025558450238175448,
      "step_index": 2180,
      "timestamp_seconds": 8.720000414177775,
      "trace_row": 2180,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09606300831101079,
      "vertical_lower_margin_m": 0.10527213006320874,
      "vertical_upper_margin_m": -0.09606300831101079
    },
    {
      "actual_left_finger_qpos_m": [
        0.022900162264704704,
        0.02240981161594391
      ],
      "angular_speed_rps": 2.4662827506787623,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0006209434326279739,
        0.16354246226377944,
        -0.0015352117212015792
      ],
      "can_pose": [
        -0.29476606845855713,
        -0.15323515236377716,
        0.9409313797950745,
        -0.00643299100920558,
        0.6827926635742188,
        0.04377689212560654,
        0.7292713522911072
      ],
      "can_relative_orientation_from_partial_start_rad": 0.052201992753912116,
      "can_relative_translation_from_partial_start_m": [
        0.0001398622989654541,
        -0.0021837949752807617,
        -0.0032094717025756836
      ],
      "can_to_box_relative_orientation_rad": 1.5203836639791937,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815847396850586,
        -6.8159050941467285
      ],
      "left_finger_qvel_mps": [
        -0.0021337259095162153,
        0.0015662263613194227
      ],
      "linear_speed_mps": 0.1239193412432518,
      "local_corner_max_m": [
        0.051485902458613814,
        0.20070856599547238,
        0.03648771153083952
      ],
      "local_corner_min_m": [
        -0.052727789323869734,
        0.1263763585320865,
        -0.039558134973242676
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07669576557562763,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11471868882766872,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025518345434125858,
      "step_index": 2181,
      "timestamp_seconds": 8.724000414367765,
      "trace_row": 2181,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09594317068197102,
      "vertical_lower_margin_m": 0.10461096321858515,
      "vertical_upper_margin_m": -0.09594317068197102
    },
    {
      "actual_left_finger_qpos_m": [
        0.022898685187101364,
        0.022410744801163673
      ],
      "angular_speed_rps": 2.7288578614207304,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000687953048645995,
        0.1630897056278502,
        -0.001936051092513491
      ],
      "can_pose": [
        -0.2951548993587494,
        -0.15329968929290771,
        0.9405088424682617,
        -0.006788955070078373,
        0.6788240671157837,
        0.043425850570201874,
        0.7329844236373901
      ],
      "can_relative_orientation_from_partial_start_rad": 0.06234784226994333,
      "can_relative_translation_from_partial_start_m": [
        7.53253698348999e-05,
        -0.002606332302093506,
        -0.0035983026027679443
      ],
      "can_to_box_relative_orientation_rad": 1.521779865052777,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815781593322754,
        -6.815841197967529
      ],
      "left_finger_qvel_mps": [
        -0.0016878198366612196,
        0.0012873329687863588
      ],
      "linear_speed_mps": 0.14445852454033384,
      "local_corner_max_m": [
        0.051383963901938806,
        0.20055707450715066,
        0.03640072131149363
      ],
      "local_corner_min_m": [
        -0.05275986999923077,
        0.12562233674854972,
        -0.040272823496520616
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07629492620431572,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11463169860832284,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025486264758764823,
      "step_index": 2182,
      "timestamp_seconds": 8.728000414557755,
      "trace_row": 2182,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0957916791936493,
      "vertical_lower_margin_m": 0.10385694143504837,
      "vertical_upper_margin_m": -0.0957916791936493
    },
    {
      "actual_left_finger_qpos_m": [
        0.022897522896528244,
        0.022412313148379326
      ],
      "angular_speed_rps": 3.0425281725781077,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0007503328255125119,
        0.16260930001595486,
        -0.0024055892793574674
      ],
      "can_pose": [
        -0.2956298291683197,
        -0.1533597707748413,
        0.9400778412818909,
        -0.007437973748892546,
        0.6743896007537842,
        0.04304303601384163,
        0.7370826601982117
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0740539822650116,
      "can_relative_translation_from_partial_start_m": [
        1.5243887901306152e-05,
        -0.0030373334884643555,
        -0.004073232412338257
      ],
      "can_to_box_relative_orientation_rad": 1.5237628159065313,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 25,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815699577331543,
        -6.81575870513916
      ],
      "left_finger_qvel_mps": [
        -0.0015759405214339495,
        0.001303234719671309
      ],
      "linear_speed_mps": 0.16103766867697936,
      "local_corner_max_m": [
        0.051281412376249,
        0.20039110985343012,
        0.036293075229506144
      ],
      "local_corner_min_m": [
        -0.052782078027274026,
        0.1248274901784796,
        -0.04110425378822108
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07582538801747174,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11452405252633535,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025464056730721565,
      "step_index": 2183,
      "timestamp_seconds": 8.732000414747745,
      "trace_row": 2183,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09562571453992876,
      "vertical_lower_margin_m": 0.10306209486497825,
      "vertical_upper_margin_m": -0.09562571453992876
    },
    {
      "actual_left_finger_qpos_m": [
        0.022896235808730125,
        0.022413400933146477
      ],
      "angular_speed_rps": 3.2481435064196775,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000815419386536953,
        0.16206149809452886,
        -0.0029235260822361164
      ],
      "can_pose": [
        -0.29614967107772827,
        -0.15342241525650024,
        0.939578652381897,
        -0.008067003451287746,
        0.6696234345436096,
        0.042632438242435455,
        0.7414324879646301
      ],
      "can_relative_orientation_from_partial_start_rad": 0.0866644615650814,
      "can_relative_translation_from_partial_start_m": [
        -4.7400593757629395e-05,
        -0.003536522388458252,
        -0.004593074321746826
      ],
      "can_to_box_relative_orientation_rad": 1.5258709541077446,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 26,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.81560754776001,
        -6.81566047668457
      ],
      "left_finger_qvel_mps": [
        -0.0014104688307270408,
        0.0010663922876119614
      ],
      "linear_speed_mps": 0.18085723824702338,
      "local_corner_max_m": [
        0.051172605876964095,
        0.20017767027000077,
        0.03615247867157079
      ],
      "local_corner_min_m": [
        -0.052803444650038,
        0.12394532591905694,
        -0.04199953083604302
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07530745121459309,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1143834559684,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.02544269010795759,
      "step_index": 2184,
      "timestamp_seconds": 8.736000414937735,
      "trace_row": 2184,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09541227495649941,
      "vertical_lower_margin_m": 0.10217993060555558,
      "vertical_upper_margin_m": -0.09541227495649941
    },
    {
      "actual_left_finger_qpos_m": [
        0.02289455756545067,
        0.022414332255721092
      ],
      "angular_speed_rps": 3.460286611749781,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0008801500968427245,
        0.1614441602282608,
        -0.003488059342941663
      ],
      "can_pose": [
        -0.29670602083206177,
        -0.15348443388938904,
        0.9390028119087219,
        -0.008579835295677185,
        0.6645054221153259,
        0.042197246104478836,
        0.746042013168335
      ],
      "can_relative_orientation_from_partial_start_rad": 0.10014229294846443,
      "can_relative_translation_from_partial_start_m": [
        -0.00010941922664642334,
        -0.004112362861633301,
        -0.005149424076080322
      ],
      "can_to_box_relative_orientation_rad": 1.5279775704436458,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 26,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815524578094482,
        -6.815572738647461
      ],
      "left_finger_qvel_mps": [
        -0.0016724683810025454,
        0.0012664746027439833
      ],
      "linear_speed_mps": 0.20077405666111184,
      "local_corner_max_m": [
        0.051061456904435976,
        0.19992073654802422,
        0.035974386706598194
      ],
      "local_corner_min_m": [
        -0.052821757098121425,
        0.12296758390849738,
        -0.04295050539248152
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07474291795388754,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1142053640034274,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025424377659874167,
      "step_index": 2185,
      "timestamp_seconds": 8.740000415127724,
      "trace_row": 2185,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09515534123452286,
      "vertical_lower_margin_m": 0.10120218859499602,
      "vertical_upper_margin_m": -0.09515534123452286
    },
    {
      "actual_left_finger_qpos_m": [
        0.022893492132425308,
        0.022416401654481888
      ],
      "angular_speed_rps": 3.842162070334576,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.000939590520229433,
        0.16081637002627902,
        -0.004130409990072026
      ],
      "can_pose": [
        -0.2973319888114929,
        -0.15354083478450775,
        0.9384127855300903,
        -0.009027544409036636,
        0.6587790250778198,
        0.0417230986058712,
        0.7511245012283325
      ],
      "can_relative_orientation_from_partial_start_rad": 0.11516187513990157,
      "can_relative_translation_from_partial_start_m": [
        -0.00016582012176513672,
        -0.004702389240264893,
        -0.005775392055511475
      ],
      "can_to_box_relative_orientation_rad": 1.5302392948145795,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 26,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815439224243164,
        -6.815494060516357
      ],
      "left_finger_qvel_mps": [
        -0.0015083902981132269,
        0.0011528986506164074
      ],
      "linear_speed_mps": 0.2155150849025924,
      "local_corner_max_m": [
        0.0509511151278611,
        0.199693605037778,
        0.03574663034351899
      ],
      "local_corner_min_m": [
        -0.05283029616831997,
        0.12193913501478004,
        -0.044007450323663044
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07410056730675718,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1139776076403482,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025415838589675624,
      "step_index": 2186,
      "timestamp_seconds": 8.744000415317714,
      "trace_row": 2186,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09492820972427664,
      "vertical_lower_margin_m": 0.10017373970127869,
      "vertical_upper_margin_m": -0.09492820972427664
    },
    {
      "actual_left_finger_qpos_m": [
        0.02289195917546749,
        0.022417690604925156
      ],
      "angular_speed_rps": 4.001373346082586,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0010029528446007796,
        0.16009476383181198,
        -0.004805596847430427
      ],
      "can_pose": [
        -0.29798582196235657,
        -0.15360106527805328,
        0.9377248287200928,
        -0.00941348448395729,
        0.6527703404426575,
        0.04124026000499725,
        0.7563740015029907
      ],
      "can_relative_orientation_from_partial_start_rad": 0.1308612025771133,
      "can_relative_translation_from_partial_start_m": [
        -0.00022605061531066895,
        -0.005390346050262451,
        -0.006429225206375122
      ],
      "can_to_box_relative_orientation_rad": 1.5325882752563262,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 26,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815362453460693,
        -6.8154144287109375
      ],
      "left_finger_qvel_mps": [
        -0.0016207197913900018,
        0.001722040120512247
      ],
      "linear_speed_mps": 0.23775118138884974,
      "local_corner_max_m": [
        0.05083538288049233,
        0.19938588264002044,
        0.03549032279268405
      ],
      "local_corner_min_m": [
        -0.05284128856969389,
        0.12080364502360352,
        -0.0451015164875449
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07342538044939878,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11372130008951326,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025404846188301702,
      "step_index": 2187,
      "timestamp_seconds": 8.748000415507704,
      "trace_row": 2187,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09462048732651908,
      "vertical_lower_margin_m": 0.09903824971010217,
      "vertical_upper_margin_m": -0.09462048732651908
    },
    {
      "actual_left_finger_qpos_m": [
        0.02289099246263504,
        0.022419508546590805
      ],
      "angular_speed_rps": 4.224777684870992,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0010699626390835992,
        0.15935046721438828,
        -0.005549928902601364
      ],
      "can_pose": [
        -0.29870137572288513,
        -0.1536651849746704,
        0.9369999766349792,
        -0.009654112160205841,
        0.6463711261749268,
        0.04081316664814949,
        0.7618698477745056
      ],
      "can_relative_orientation_from_partial_start_rad": 0.14744915787998697,
      "can_relative_translation_from_partial_start_m": [
        -0.0002901703119277954,
        -0.0061151981353759766,
        -0.0071447789669036865
      ],
      "can_to_box_relative_orientation_rad": 1.5348525886126745,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 27,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815269947052002,
        -6.815322399139404
      ],
      "left_finger_qvel_mps": [
        -0.001441259984858334,
        0.0010926772374659777
      ],
      "linear_speed_mps": 0.2551395409934254,
      "local_corner_max_m": [
        0.05072064723273237,
        0.19908438814274865,
        0.03517287388987961
      ],
      "local_corner_min_m": [
        -0.052860572510899595,
        0.11961654628602791,
        -0.046272731695082336
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07268104839422784,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11340385118670882,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025385562247095997,
      "step_index": 2188,
      "timestamp_seconds": 8.752000415697694,
      "trace_row": 2188,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09431899282924729,
      "vertical_lower_margin_m": 0.09785115097252656,
      "vertical_upper_margin_m": -0.09431899282924729
    },
    {
      "actual_left_finger_qpos_m": [
        0.022889394313097,
        0.022420821711421013
      ],
      "angular_speed_rps": 4.3411569544714705,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0011384695237169895,
        0.15851587013309731,
        -0.006333352586595231
      ],
      "can_pose": [
        -0.2994515895843506,
        -0.15373073518276215,
        0.9361807703971863,
        -0.009834221564233303,
        0.639745831489563,
        0.04038558527827263,
        0.7674620151519775
      ],
      "can_relative_orientation_from_partial_start_rad": 0.16453764322635778,
      "can_relative_translation_from_partial_start_m": [
        -0.00035572052001953125,
        -0.006934404373168945,
        -0.00789499282836914
      ],
      "can_to_box_relative_orientation_rad": 1.5372146356373741,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 27,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8151774406433105,
        -6.815231800079346
      ],
      "left_finger_qvel_mps": [
        -0.0016990071162581444,
        0.0015123668126761913
      ],
      "linear_speed_mps": 0.2781879322205626,
      "local_corner_max_m": [
        0.050604065440911505,
        0.19869821849384428,
        0.03481365994599056
      ],
      "local_corner_min_m": [
        -0.052881004488345484,
        0.11833352177235035,
        -0.04748036511918102
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07189762471023398,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11304463724281977,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025365130269650107,
      "step_index": 2189,
      "timestamp_seconds": 8.756000415887684,
      "trace_row": 2189,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09393282318034292,
      "vertical_lower_margin_m": 0.09656812645884899,
      "vertical_upper_margin_m": -0.09393282318034292
    },
    {
      "actual_left_finger_qpos_m": [
        0.02288859896361828,
        0.02242382988333702
      ],
      "angular_speed_rps": 4.757041318084999,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0011990985218223449,
        0.15769798473217023,
        -0.007205696638818093
      ],
      "can_pose": [
        -0.3002840578556061,
        -0.1537884771823883,
        0.9353685975074768,
        -0.00992134865373373,
        0.6324254870414734,
        0.039984505623579025,
        0.7735251188278198
      ],
      "can_relative_orientation_from_partial_start_rad": 0.18328587164081844,
      "can_relative_translation_from_partial_start_m": [
        -0.0004134625196456909,
        -0.007746577262878418,
        -0.008727461099624634
      ],
      "can_to_box_relative_orientation_rad": 1.5397238727277776,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 27,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.815098285675049,
        -6.815152168273926
      ],
      "left_finger_qvel_mps": [
        -0.0014454927295446396,
        0.0011466073337942362
      ],
      "linear_speed_mps": 0.29111447867821993,
      "local_corner_max_m": [
        0.0504969958859931,
        0.19836956252183946,
        0.034390132808776064
      ],
      "local_corner_min_m": [
        -0.05289519292963779,
        0.117026406942501,
        -0.04880152608641225
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07102528065801111,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11262111010560527,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0253509418283578,
      "step_index": 2190,
      "timestamp_seconds": 8.760000416077673,
      "trace_row": 2190,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0936041672083381,
      "vertical_lower_margin_m": 0.09526101162899964,
      "vertical_upper_margin_m": -0.0936041672083381
    },
    {
      "actual_left_finger_qpos_m": [
        0.022886933758854866,
        0.022424757480621338
      ],
      "angular_speed_rps": 4.812590464008589,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0012635907472333119,
        0.15674406587929324,
        -0.008088800247983696
      ],
      "can_pose": [
        -0.3011249303817749,
        -0.15385010838508606,
        0.9344174861907959,
        -0.009967503137886524,
        0.6249604225158691,
        0.03959258645772934,
        0.7795881628990173
      ],
      "can_relative_orientation_from_partial_start_rad": 0.2022932281769662,
      "can_relative_translation_from_partial_start_m": [
        -0.0004750937223434448,
        -0.008697688579559326,
        -0.009568333625793457
      ],
      "can_to_box_relative_orientation_rad": 1.542365602723454,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 27,
        "physical_hit": true
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814995765686035,
        -6.815049171447754
      ],
      "left_finger_qvel_mps": [
        -0.0017099769320338964,
        0.0013600497040897608
      ],
      "linear_speed_mps": 0.31775359888479826,
      "local_corner_max_m": [
        0.05038673105927907,
        0.19789934739415838,
        0.03394522457311727
      ],
      "local_corner_min_m": [
        -0.05291391255374567,
        0.1155887843644281,
        -0.050122825069084664
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.07014217704884551,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11217620186994648,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025332222204249924,
      "step_index": 2191,
      "timestamp_seconds": 8.764000416267663,
      "trace_row": 2191,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09313395208065701,
      "vertical_lower_margin_m": 0.09382338905092674,
      "vertical_upper_margin_m": -0.09313395208065701
    },
    {
      "actual_left_finger_qpos_m": [
        0.022885028272867203,
        0.022425392642617226
      ],
      "angular_speed_rps": 4.8533767134629935,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0013285968757006938,
        0.15565393912538938,
        -0.00898473279270584
      ],
      "can_pose": [
        -0.30197733640670776,
        -0.15391229093074799,
        0.9333285093307495,
        -0.009988580830395222,
        0.6173728108406067,
        0.03920786827802658,
        0.7856296896934509
      ],
      "can_relative_orientation_from_partial_start_rad": 0.22149669551611778,
      "can_relative_translation_from_partial_start_m": [
        -0.0005372762680053711,
        -0.009786665439605713,
        -0.010420739650726318
      ],
      "can_to_box_relative_orientation_rad": 1.5451641264913478,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 27,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814924716949463,
        -6.814976215362549
      ],
      "left_finger_qvel_mps": [
        -0.0016796294366940856,
        0.0011556582758203149
      ],
      "linear_speed_mps": 0.3460792105863776,
      "local_corner_max_m": [
        0.050276401080808636,
        0.1972840707380361,
        0.03347577473287888
      ],
      "local_corner_min_m": [
        -0.052933594832209996,
        0.11402380751274266,
        -0.051445240318290564
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.06924624450412337,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11170675202970809,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025312539925785596,
      "step_index": 2192,
      "timestamp_seconds": 8.768000416457653,
      "trace_row": 2192,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09251867542453475,
      "vertical_lower_margin_m": 0.0922584121992413,
      "vertical_upper_margin_m": -0.09251867542453475
    },
    {
      "actual_left_finger_qpos_m": [
        0.02288311906158924,
        0.022426005452871323
      ],
      "angular_speed_rps": 4.8523922758863645,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0013936035998616259,
        0.1544070321794101,
        -0.009880637654039626
      ],
      "can_pose": [
        -0.3028297424316406,
        -0.1539745032787323,
        0.932083010673523,
        -0.010004852898418903,
        0.6097283363342285,
        0.03882436081767082,
        0.791595995426178
      ],
      "can_relative_orientation_from_partial_start_rad": 0.24072864181374481,
      "can_relative_translation_from_partial_start_m": [
        -0.0005994886159896851,
        -0.011032164096832275,
        -0.01127314567565918
      ],
      "can_to_box_relative_orientation_rad": 1.5481389860117738,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 25,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814838886260986,
        -6.814890384674072
      ],
      "left_finger_qvel_mps": [
        -0.0017491262406110764,
        0.0012263854732736945
      ],
      "linear_speed_mps": 0.3776351658664513,
      "local_corner_max_m": [
        0.0501659255753141,
        0.19649683483458957,
        0.03299147938780572
      ],
      "local_corner_min_m": [
        -0.052953132775037326,
        0.11231722952423062,
        -0.052752754695884974
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.06835033964278958,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11122245668463493,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.025293001982958266,
      "step_index": 2193,
      "timestamp_seconds": 8.772000416647643,
      "trace_row": 2193,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09173143952108821,
      "vertical_lower_margin_m": 0.09055183421072927,
      "vertical_upper_margin_m": -0.09173143952108821
    },
    {
      "actual_left_finger_qpos_m": [
        0.022881172597408295,
        0.02242666855454445
      ],
      "angular_speed_rps": 4.8513777780688505,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.001458625728989471,
        0.15300340529381418,
        -0.010776542700553504
      ],
      "can_pose": [
        -0.3036821782588959,
        -0.1540367603302002,
        0.930681049823761,
        -0.010016338899731636,
        0.6020277738571167,
        0.03844211623072624,
        0.7974864840507507
      ],
      "can_relative_orientation_from_partial_start_rad": 0.2599817420117493,
      "can_relative_translation_from_partial_start_m": [
        -0.0006617456674575806,
        -0.012434124946594238,
        -0.012125581502914429
      ],
      "can_to_box_relative_orientation_rad": 1.5512889785687896,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 24,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814751625061035,
        -6.814806938171387
      ],
      "left_finger_qvel_mps": [
        -0.0018422885332256556,
        0.0013372509274631739
      ],
      "linear_speed_mps": 0.41048879005729616,
      "local_corner_max_m": [
        0.05005531816479711,
        0.19553753304106902,
        0.03249214574721304
      ],
      "local_corner_min_m": [
        -0.05297256962277608,
        0.11046927754655933,
        -0.05404523114832005
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0674544345962757,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11072312304404225,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.024185746148509157,
      "step_index": 2194,
      "timestamp_seconds": 8.776000416837633,
      "trace_row": 2194,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.09077213772756766,
      "vertical_lower_margin_m": 0.08870388223305797,
      "vertical_upper_margin_m": -0.09077213772756766
    },
    {
      "actual_left_finger_qpos_m": [
        0.022879529744386673,
        0.02242717146873474
      ],
      "angular_speed_rps": 4.850806369959154,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.001523632165270905,
        0.15144241776614187,
        -0.011672407799347972
      ],
      "can_pose": [
        -0.3045346140861511,
        -0.15409903228282928,
        0.9291219711303711,
        -0.010023077949881554,
        0.5942712426185608,
        0.03806135803461075,
        0.8033012747764587
      ],
      "can_relative_orientation_from_partial_start_rad": 0.2792525277576809,
      "can_relative_translation_from_partial_start_m": [
        -0.0007240176200866699,
        -0.01399320363998413,
        -0.012978017330169678
      ],
      "can_to_box_relative_orientation_rad": 1.5546129304748553,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814651966094971,
        -6.814711093902588
      ],
      "left_finger_qvel_mps": [
        -0.0016803587786853313,
        0.0012100348249077797
      ],
      "linear_speed_mps": 0.44449765941117486,
      "local_corner_max_m": [
        0.04994465031501519,
        0.19440541918250576,
        0.031977704562253906
      ],
      "local_corner_min_m": [
        -0.05299191464555697,
        0.10847941634977798,
        -0.05532252016094985
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.06655856949748123,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.11020868185908311,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.022908457135879357,
      "step_index": 2195,
      "timestamp_seconds": 8.780000417027622,
      "trace_row": 2195,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0896400238690044,
      "vertical_lower_margin_m": 0.08671402103627662,
      "vertical_upper_margin_m": -0.0896400238690044
    },
    {
      "actual_left_finger_qpos_m": [
        0.022877763956785202,
        0.0224277526140213
      ],
      "angular_speed_rps": 4.8498563680065105,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0015886389429651815,
        0.14972471316643032,
        -0.012568270439456408
      ],
      "can_pose": [
        -0.30538707971572876,
        -0.15416133403778076,
        0.9274064302444458,
        -0.010025064460933208,
        0.5864599943161011,
        0.03768197074532509,
        0.8090392351150513
      ],
      "can_relative_orientation_from_partial_start_rad": 0.29853561969284076,
      "can_relative_translation_from_partial_start_m": [
        -0.000786319375038147,
        -0.015708744525909424,
        -0.013830482959747314
      ],
      "can_to_box_relative_orientation_rad": 1.5581095379444976,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 24,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8145670890808105,
        -6.8146233558654785
      ],
      "left_finger_qvel_mps": [
        -0.001703660935163498,
        0.001230268506333232
      ],
      "linear_speed_mps": 0.479169812056726,
      "local_corner_max_m": [
        0.049833921794946334,
        0.19310093628882785,
        0.031447922755500624
      ],
      "local_corner_min_m": [
        -0.0530111996808767,
        0.1063484900440328,
        -0.05658446363441344
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0656627068573728,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10967890005232983,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.021646513662415767,
      "step_index": 2196,
      "timestamp_seconds": 8.784000417217612,
      "trace_row": 2196,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.08833554097532649,
      "vertical_lower_margin_m": 0.08458309473053144,
      "vertical_upper_margin_m": -0.08833554097532649
    },
    {
      "actual_left_finger_qpos_m": [
        0.022875983268022537,
        0.02242838218808174
      ],
      "angular_speed_rps": 4.848832846930336,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0016536461347512466,
        0.14785017053723615,
        -0.013464099598582635
      ],
      "can_pose": [
        -0.3062395453453064,
        -0.15422366559505463,
        0.9255343079566956,
        -0.010022328235208988,
        0.5785950422286987,
        0.03730399161577225,
        0.8146999478340149
      ],
      "can_relative_orientation_from_partial_start_rad": 0.3178277868865515,
      "can_relative_translation_from_partial_start_m": [
        -0.0008486509323120117,
        -0.017580866813659668,
        -0.014682948589324951
      ],
      "can_to_box_relative_orientation_rad": 1.5617774554911934,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 23,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814478874206543,
        -6.8145341873168945
      ],
      "left_finger_qvel_mps": [
        -0.0018213141011074185,
        0.0013720763381570578
      ],
      "linear_speed_mps": 0.5145036643814392,
      "local_corner_max_m": [
        0.049723158325794575,
        0.19162380832256076,
        0.03090267985775491
      ],
      "local_corner_min_m": [
        -0.053030450595297096,
        0.10407653275191153,
        -0.05783087905492018
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.06476687769824657,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10913365715458412,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.020400098241909026,
      "step_index": 2197,
      "timestamp_seconds": 8.788000417407602,
      "trace_row": 2197,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0868584130090594,
      "vertical_lower_margin_m": 0.08231113743841018,
      "vertical_upper_margin_m": -0.0868584130090594
    },
    {
      "actual_left_finger_qpos_m": [
        0.022874150425195694,
        0.02242899499833584
      ],
      "angular_speed_rps": 4.847902006099104,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0017186536460639945,
        0.1458183143724323,
        -0.0143598937633726
      ],
      "can_pose": [
        -0.30709201097488403,
        -0.15428602695465088,
        0.9235051274299622,
        -0.010014892555773258,
        0.5706769824028015,
        0.0369274728000164,
        0.8202829957008362
      ],
      "can_relative_orientation_from_partial_start_rad": 0.3371271288033746,
      "can_relative_translation_from_partial_start_m": [
        -0.0009110122919082642,
        -0.019610047340393066,
        -0.015535414218902588
      ],
      "can_to_box_relative_orientation_rad": 1.5656153571601337,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 25,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.81437873840332,
        -6.8144354820251465
      ],
      "left_finger_qvel_mps": [
        -0.0016743185697123408,
        0.0011767437681555748
      ],
      "linear_speed_mps": 0.5504634262547244,
      "local_corner_max_m": [
        0.04961238719297806,
        0.1899734275495778,
        0.03034184589916461
      ],
      "local_corner_min_m": [
        -0.05304969448510605,
        0.10166320119528682,
        -0.05906163342590981
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.06387108353345661,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10857282319599382,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.019169343870919398,
      "step_index": 2198,
      "timestamp_seconds": 8.792000417597592,
      "trace_row": 2198,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.08520803223607644,
      "vertical_lower_margin_m": 0.07989780588178547,
      "vertical_upper_margin_m": -0.08520803223607644
    },
    {
      "actual_left_finger_qpos_m": [
        0.022872373461723328,
        0.022429542616009712
      ],
      "angular_speed_rps": 4.846874170123577,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0017836465140669278,
        0.14362968165602186,
        -0.01525568109731934
      ],
      "can_pose": [
        -0.30794450640678406,
        -0.15434840321540833,
        0.9213194251060486,
        -0.010002773255109787,
        0.562706708908081,
        0.036552462726831436,
        0.8257877230644226
      ],
      "can_relative_orientation_from_partial_start_rad": 0.3564314797991915,
      "can_relative_translation_from_partial_start_m": [
        -0.0009733885526657104,
        -0.02179574966430664,
        -0.016387909650802612
      ],
      "can_to_box_relative_orientation_rad": 1.5696217359276505,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 24,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814298629760742,
        -6.814350128173828
      ],
      "left_finger_qvel_mps": [
        -0.001723887282423675,
        0.001240439130924642
      ],
      "linear_speed_mps": 0.586724668437637,
      "local_corner_max_m": [
        0.04950165079000965,
        0.1881501887129503,
        0.02976525234027222
      ],
      "local_corner_min_m": [
        -0.05306894381814348,
        0.09910917459909341,
        -0.0602766145349109
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.06297529619950987,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10799622963710143,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.017954362761918308,
      "step_index": 2199,
      "timestamp_seconds": 8.796000417787582,
      "trace_row": 2199,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.08338479339944894,
      "vertical_lower_margin_m": 0.07734377928559205,
      "vertical_upper_margin_m": -0.08338479339944894
    },
    {
      "actual_left_finger_qpos_m": [
        0.0228706207126379,
        0.02243008278310299
      ],
      "angular_speed_rps": 4.845956892847424,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0018486544501206958,
        0.1412843331304937,
        -0.016151430119809296
      ],
      "can_pose": [
        -0.3087970018386841,
        -0.15441082417964935,
        0.9189772605895996,
        -0.009985999204218388,
        0.5546848177909851,
        0.036179013550281525,
        0.8312137722969055
      ],
      "can_relative_orientation_from_partial_start_rad": 0.37573986730245,
      "can_relative_translation_from_partial_start_m": [
        -0.0010358095169067383,
        -0.024137914180755615,
        -0.017240405082702637
      ],
      "can_to_box_relative_orientation_rad": 1.573795204508481,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 20,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.81420373916626,
        -6.814251899719238
      ],
      "left_finger_qvel_mps": [
        -0.0017209023935720325,
        0.0012326773721724749
      ],
      "linear_speed_mps": 0.6233166766267132,
      "local_corner_max_m": [
        0.04939094584527248,
        0.1861540330070185,
        0.02917281217461376
      ],
      "local_corner_min_m": [
        -0.053088254745513874,
        0.09641463325396893,
        -0.06147567241423235
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.06207954717701991,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10740378947144297,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.016755304882596855,
      "step_index": 2200,
      "timestamp_seconds": 8.800000417977571,
      "trace_row": 2200,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.08138863769351713,
      "vertical_lower_margin_m": 0.07464923794046757,
      "vertical_upper_margin_m": -0.08138863769351713
    },
    {
      "actual_left_finger_qpos_m": [
        0.02286883071064949,
        0.02243068255484104
      ],
      "angular_speed_rps": 4.844876678265653,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.001913647594729534,
        0.1387816134717088,
        -0.01704716881253998
      ],
      "can_pose": [
        -0.3096495270729065,
        -0.15447326004505157,
        0.9164779782295227,
        -0.009964588098227978,
        0.5466124415397644,
        0.035807181149721146,
        0.8365606069564819
      ],
      "can_relative_orientation_from_partial_start_rad": 0.3950505032891611,
      "can_relative_translation_from_partial_start_m": [
        -0.00109824538230896,
        -0.02663719654083252,
        -0.01809293031692505
      ],
      "can_to_box_relative_orientation_rad": 1.5781341092848806,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 18,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814107418060303,
        -6.8141679763793945
      ],
      "left_finger_qvel_mps": [
        -0.0017755996668711305,
        0.001306438585743308
      ],
      "linear_speed_mps": 0.6603554518626816,
      "local_corner_max_m": [
        0.04928032936944676,
        0.18398417092797503,
        0.028564365571775663
      ],
      "local_corner_min_m": [
        -0.05310762455890583,
        0.09357905601544259,
        -0.06265870319685563
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.061183808484289226,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10679534286860487,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.015572274099973582,
      "step_index": 2201,
      "timestamp_seconds": 8.804000418167561,
      "trace_row": 2201,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.07921877561447367,
      "vertical_lower_margin_m": 0.07181366070194123,
      "vertical_upper_margin_m": -0.07921877561447367
    },
    {
      "actual_left_finger_qpos_m": [
        0.022867197170853615,
        0.022431226447224617
      ],
      "angular_speed_rps": 4.8439962205673455,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0019786558270498134,
        0.1361221187438144,
        -0.017942897514405753
      ],
      "can_pose": [
        -0.3105020821094513,
        -0.15453574061393738,
        0.9138221740722656,
        -0.009938564151525497,
        0.5384899973869324,
        0.03543699160218239,
        0.841827929019928
      ],
      "can_relative_orientation_from_partial_start_rad": 0.41436325839765636,
      "can_relative_translation_from_partial_start_m": [
        -0.0011607259511947632,
        -0.0292930006980896,
        -0.01894548535346985
      ],
      "can_to_box_relative_orientation_rad": 1.58263708439681,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 16,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.814023494720459,
        -6.814077854156494
      ],
      "left_finger_qvel_mps": [
        -0.0015500737354159355,
        0.0011249907547608018
      ],
      "linear_speed_mps": 0.6974977103047186,
      "local_corner_max_m": [
        0.04916979523522785,
        0.1816410957590775,
        0.02793980943858443
      ],
      "local_corner_min_m": [
        -0.05312710688932748,
        0.09060314172855133,
        -0.06382560446739594
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.060288079782423454,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10617078673541364,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.014405372829433272,
      "step_index": 2202,
      "timestamp_seconds": 8.808000418357551,
      "trace_row": 2202,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.07687570044557614,
      "vertical_lower_margin_m": 0.06883774641504997,
      "vertical_upper_margin_m": -0.07687570044557614
    },
    {
      "actual_left_finger_qpos_m": [
        0.022865597158670425,
        0.02243174985051155
      ],
      "angular_speed_rps": 4.842974773607917,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002043649157924765,
        0.13330585037598008,
        -0.01883858318088466
      ],
      "can_pose": [
        -0.3113546371459961,
        -0.15459823608398438,
        0.9110098481178284,
        -0.009907953441143036,
        0.530318558216095,
        0.03506851568818092,
        0.8470152020454407
      ],
      "can_relative_orientation_from_partial_start_rad": 0.4336768089493637,
      "can_relative_translation_from_partial_start_m": [
        -0.0012232214212417603,
        -0.032105326652526855,
        -0.01979804039001465
      ],
      "can_to_box_relative_orientation_rad": 1.5873023998292974,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 15,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813935279846191,
        -6.813979625701904
      ],
      "left_finger_qvel_mps": [
        -0.0016476291930302978,
        0.001216275617480278
      ],
      "linear_speed_mps": 0.7348440407395207,
      "local_corner_max_m": [
        0.04905940122561714,
        0.17912469026387767,
        0.027299060802329744
      ],
      "local_corner_min_m": [
        -0.05314669954146667,
        0.0874870104880825,
        -0.06497622716409907
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.05939239411594455,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10553003809915895,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.013254750132730142,
      "step_index": 2203,
      "timestamp_seconds": 8.812000418547541,
      "trace_row": 2203,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.07435929495037631,
      "vertical_lower_margin_m": 0.06572161517458114,
      "vertical_upper_margin_m": -0.07435929495037631
    },
    {
      "actual_left_finger_qpos_m": [
        0.02286382019519806,
        0.022432364523410797
      ],
      "angular_speed_rps": 4.842023894411942,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0021086424739938103,
        0.13033227261036107,
        -0.019734284634284116
      ],
      "can_pose": [
        -0.31220725178718567,
        -0.15466076135635376,
        0.908040463924408,
        -0.009872776456177235,
        0.5220986604690552,
        0.03470178693532944,
        0.8521218299865723
      ],
      "can_relative_orientation_from_partial_start_rad": 0.4529908042928256,
      "can_relative_translation_from_partial_start_m": [
        -0.001285746693611145,
        -0.035074710845947266,
        -0.020650655031204224
      ],
      "can_to_box_relative_orientation_rad": 1.5921284951522752,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 14,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813845157623291,
        -6.813897609710693
      ],
      "left_finger_qvel_mps": [
        -0.0018580970354378223,
        0.00141216441988945
      ],
      "linear_speed_mps": 0.7725001099178548,
      "local_corner_max_m": [
        0.04894915727350349,
        0.17643431963053258,
        0.026641962448638534
      ],
      "local_corner_min_m": [
        -0.05316644222149114,
        0.08423022559018956,
        -0.06611053171720677
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.05849669266254509,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10487293974546774,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.01212044557962244,
      "step_index": 2204,
      "timestamp_seconds": 8.81600041873753,
      "trace_row": 2204,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.07166892431703122,
      "vertical_lower_margin_m": 0.0624648302766882,
      "vertical_upper_margin_m": -0.07166892431703122
    },
    {
      "actual_left_finger_qpos_m": [
        0.022862132638692856,
        0.022432899102568626
      ],
      "angular_speed_rps": 4.841076617589937,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002173635717110295,
        0.1272019226801011,
        -0.020629940758013554
      ],
      "can_pose": [
        -0.31305986642837524,
        -0.15472331643104553,
        0.9049145579338074,
        -0.009833061136305332,
        0.5138312578201294,
        0.034336864948272705,
        0.8571476340293884
      ],
      "can_relative_orientation_from_partial_start_rad": 0.4723047300155563,
      "can_relative_translation_from_partial_start_m": [
        -0.0013483017683029175,
        -0.03820061683654785,
        -0.0215032696723938
      ],
      "can_to_box_relative_orientation_rad": 1.5971137162121918,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 9,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813753604888916,
        -6.813811302185059
      ],
      "left_finger_qvel_mps": [
        -0.0018398830434307456,
        0.0013820098247379065
      ],
      "linear_speed_mps": 0.8101756031936151,
      "local_corner_max_m": [
        0.048839088646185636,
        0.1735704238300425,
        0.0259684795951598
      ],
      "local_corner_min_m": [
        -0.053186360080406225,
        0.08083342153015971,
        -0.06722836111118691
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.05760103653881565,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.104199456891989,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0110026161856423,
      "step_index": 2205,
      "timestamp_seconds": 8.82000041892752,
      "trace_row": 2205,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.06880502851654115,
      "vertical_lower_margin_m": 0.059068026216658354,
      "vertical_upper_margin_m": -0.06880502851654115
    },
    {
      "actual_left_finger_qpos_m": [
        0.022860461845993996,
        0.022433502599596977
      ],
      "angular_speed_rps": 4.840072898079613,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002238628904271206,
        0.1239148003535625,
        -0.02152558032545021
      ],
      "can_pose": [
        -0.3139125108718872,
        -0.1547859013080597,
        0.9016321301460266,
        -0.009788828901946545,
        0.5055171847343445,
        0.03397378325462341,
        0.8620920181274414
      ],
      "can_relative_orientation_from_partial_start_rad": 0.4916179149345247,
      "can_relative_translation_from_partial_start_m": [
        -0.0014108866453170776,
        -0.04148304462432861,
        -0.02235591411590576
      ],
      "can_to_box_relative_orientation_rad": 1.6022563291251393,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 9,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813652038574219,
        -6.813709259033203
      ],
      "left_finger_qvel_mps": [
        -0.0015304922126233578,
        0.00110278045758605
      ],
      "linear_speed_mps": 0.8479847619112117,
      "local_corner_max_m": [
        0.04872921958089904,
        0.1705329075766533,
        0.025278490359597783
      ],
      "local_corner_min_m": [
        -0.05320647738944145,
        0.07729669313047172,
        -0.0683296510104982
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.056705396971378996,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10350946765642699,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.009901326286331003,
      "step_index": 2206,
      "timestamp_seconds": 8.82400041911751,
      "trace_row": 2206,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.06576751226315193,
      "vertical_lower_margin_m": 0.05553129781697036,
      "vertical_upper_margin_m": -0.06576751226315193
    },
    {
      "actual_left_finger_qpos_m": [
        0.0228587593883276,
        0.022434035316109657
      ],
      "angular_speed_rps": 4.839082770707176,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.00230362188830896,
        0.12047031148527132,
        -0.022421171264648432
      ],
      "can_pose": [
        -0.31476515531539917,
        -0.15484851598739624,
        0.8981925845146179,
        -0.009740106761455536,
        0.49715718626976013,
        0.03361260145902634,
        0.866954505443573
      ],
      "can_relative_orientation_from_partial_start_rad": 0.5109300342099979,
      "can_relative_translation_from_partial_start_m": [
        -0.0014735013246536255,
        -0.044922590255737305,
        -0.023208558559417725
      ],
      "can_to_box_relative_orientation_rad": 1.607554610018357,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 9,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8135666847229,
        -6.81361198425293
      ],
      "left_finger_qvel_mps": [
        -0.0017408307176083326,
        0.0012662999797612429
      ],
      "linear_speed_mps": 0.8860514976002463,
      "local_corner_max_m": [
        0.04861957582644871,
        0.16732109416096252,
        0.024571945280800866
      ],
      "local_corner_min_m": [
        -0.05322681960306663,
        0.07361952880958011,
        -0.06941428781009773
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.055809806032180775,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10280292257763007,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.008816689486731477,
      "step_index": 2207,
      "timestamp_seconds": 8.8280004193075,
      "trace_row": 2207,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.06255569884746116,
      "vertical_lower_margin_m": 0.05185413349607876,
      "vertical_upper_margin_m": -0.06255569884746116
    },
    {
      "actual_left_finger_qpos_m": [
        0.022857114672660828,
        0.02243456430733204
      ],
      "angular_speed_rps": 4.838089843713126,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0023685998016397536,
        0.11686911166192537,
        -0.023316772596164992
      ],
      "can_pose": [
        -0.3156178593635559,
        -0.15491114556789398,
        0.8945965766906738,
        -0.00968691986054182,
        0.48875221610069275,
        0.03325336426496506,
        0.8717349171638489
      ],
      "can_relative_orientation_from_partial_start_rad": 0.5302407526217129,
      "can_relative_translation_from_partial_start_m": [
        -0.0015361309051513672,
        -0.048518598079681396,
        -0.024061262607574463
      ],
      "can_to_box_relative_orientation_rad": 1.6130068195876384,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 10,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813474178314209,
        -6.813528060913086
      ],
      "left_finger_qvel_mps": [
        -0.0017521105473861098,
        0.0013161541428416967
      ],
      "linear_speed_mps": 0.9240636351908709,
      "local_corner_max_m": [
        0.04851019551371202,
        0.16393556014592348,
        0.023848707593117302
      ],
      "local_corner_min_m": [
        -0.05324739511699156,
        0.06980266317792727,
        -0.07048225278544729
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.054914204700664215,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.10207968488994651,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.007748724511381921,
      "step_index": 2208,
      "timestamp_seconds": 8.83200041949749,
      "trace_row": 2208,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.059170164832422115,
      "vertical_lower_margin_m": 0.048037267864425914,
      "vertical_upper_margin_m": -0.059170164832422115
    },
    {
      "actual_left_finger_qpos_m": [
        0.02285553514957428,
        0.022435033693909645
      ],
      "angular_speed_rps": 4.837133004299129,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0024335775123359715,
        0.1131111417615166,
        -0.024212353124620112
      ],
      "can_pose": [
        -0.31647059321403503,
        -0.1549738049507141,
        0.8908440470695496,
        -0.009629296138882637,
        0.48030292987823486,
        0.03289610892534256,
        0.8764327168464661
      ],
      "can_relative_orientation_from_partial_start_rad": 0.5495499360499767,
      "can_relative_translation_from_partial_start_m": [
        -0.0015987902879714966,
        -0.052271127700805664,
        -0.02491399645805359
      ],
      "can_to_box_relative_orientation_rad": 1.6186112348633477,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 7,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813378810882568,
        -6.8134355545043945
      ],
      "left_finger_qvel_mps": [
        -0.0016673681093379855,
        0.0012217226903885603
      ],
      "linear_speed_mps": 0.9621771656088675,
      "local_corner_max_m": [
        0.04840108707368357,
        0.16037617590119402,
        0.023108739482932794
      ],
      "local_corner_min_m": [
        -0.05326824209835551,
        0.06584610762183918,
        -0.07153344573217302
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.054018624172209095,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.101339716779762,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0066975315646561895,
      "step_index": 2209,
      "timestamp_seconds": 8.83600041968748,
      "trace_row": 2209,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.05561078058769266,
      "vertical_lower_margin_m": 0.04408071230833782,
      "vertical_upper_margin_m": -0.05561078058769266
    },
    {
      "actual_left_finger_qpos_m": [
        0.02285403572022915,
        0.022435469552874565
      ],
      "angular_speed_rps": 4.836139481725132,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0024985698398887757,
        0.10919580693295028,
        -0.02510791111923666
      ],
      "can_pose": [
        -0.31732335686683655,
        -0.15503650903701782,
        0.8869343996047974,
        -0.009567261673510075,
        0.4718102514743805,
        0.03254089131951332,
        0.8810475468635559
      ],
      "can_relative_orientation_from_partial_start_rad": 0.5688571966027726,
      "can_relative_translation_from_partial_start_m": [
        -0.0016614943742752075,
        -0.05618077516555786,
        -0.025766760110855103
      ],
      "can_to_box_relative_orientation_rad": 1.6243660136824825,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 6,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813281059265137,
        -6.8133320808410645
      ],
      "left_finger_qvel_mps": [
        -0.0015777228400111198,
        0.0011621554149314761
      ],
      "linear_speed_mps": 1.0005148495630234,
      "local_corner_max_m": [
        0.04829225977538884,
        0.15664227996142355,
        0.022351977306747595
      ],
      "local_corner_min_m": [
        -0.053289399455166364,
        0.06174933390447701,
        -0.07256779954522091
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.05312306617759255,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.1005829546035768,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.005663177751608295,
      "step_index": 2210,
      "timestamp_seconds": 8.84000041987747,
      "trace_row": 2210,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.051876884647922186,
      "vertical_lower_margin_m": 0.039983938590975654,
      "vertical_upper_margin_m": -0.051876884647922186
    },
    {
      "actual_left_finger_qpos_m": [
        0.022852499037981033,
        0.02243587002158165
      ],
      "angular_speed_rps": 4.835187247288927,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002563561864261127,
        0.10512376355759401,
        -0.026003445678534187
      ],
      "can_pose": [
        -0.31817615032196045,
        -0.15509924292564392,
        0.8828682899475098,
        -0.009500842541456223,
        0.4632749557495117,
        0.03218775615096092,
        0.8855791091918945
      ],
      "can_relative_orientation_from_partial_start_rad": 0.5881624893089541,
      "can_relative_translation_from_partial_start_m": [
        -0.0017242282629013062,
        -0.06024688482284546,
        -0.026619553565979004
      ],
      "can_to_box_relative_orientation_rad": 1.6302693919602094,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 6,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813200950622559,
        -6.813247203826904
      ],
      "left_finger_qvel_mps": [
        -0.0015086374478414655,
        0.0010330183431506157
      ],
      "linear_speed_mps": 1.0387624344303328,
      "local_corner_max_m": [
        0.04818375118233664,
        0.1527344711670885,
        0.021578365197858496
      ],
      "local_corner_min_m": [
        -0.053310874910858896,
        0.05751305594809952,
        -0.07358525655492687
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.05222753161829502,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.0998093424946877,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.004645720741902337,
      "step_index": 2211,
      "timestamp_seconds": 8.84400042006746,
      "trace_row": 2211,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.04796907585358713,
      "vertical_lower_margin_m": 0.035747660634598166,
      "vertical_upper_margin_m": -0.04796907585358713
    },
    {
      "actual_left_finger_qpos_m": [
        0.022850820794701576,
        0.022436337545514107
      ],
      "angular_speed_rps": 4.834193315225111,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002628538596007729,
        0.10089495314772146,
        -0.0268989547728834
      ],
      "can_pose": [
        -0.31902897357940674,
        -0.1551619917154312,
        0.878645658493042,
        -0.009430065751075745,
        0.4546978175640106,
        0.031836748123168945,
        0.8900267481803894
      ],
      "can_relative_orientation_from_partial_start_rad": 0.6074654644306741,
      "can_relative_translation_from_partial_start_m": [
        -0.0017869770526885986,
        -0.06446951627731323,
        -0.027472376823425293
      ],
      "can_to_box_relative_orientation_rad": 1.6363194847468419,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 5,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813108921051025,
        -6.8131513595581055
      ],
      "left_finger_qvel_mps": [
        -0.001690076431259513,
        0.0012350368779152632
      ],
      "linear_speed_mps": 1.0770869149017064,
      "local_corner_max_m": [
        0.048075599591893725,
        0.1486526372253465,
        0.020787852991716982
      ],
      "local_corner_min_m": [
        -0.05333267678390918,
        0.053137269070096416,
        -0.07458576253748378
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.05133202252394581,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.09901883028854619,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0036452147593454276,
      "step_index": 2212,
      "timestamp_seconds": 8.84800042025745,
      "trace_row": 2212,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.043887241911845135,
      "vertical_lower_margin_m": 0.03137187375659506,
      "vertical_upper_margin_m": -0.043887241911845135
    },
    {
      "actual_left_finger_qpos_m": [
        0.02284923940896988,
        0.02243676967918873
      ],
      "angular_speed_rps": 4.833229138331716,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0026935149428075067,
        0.09650878004431807,
        -0.02779446745969355
      ],
      "can_pose": [
        -0.3198818564414978,
        -0.1552247703075409,
        0.8742659091949463,
        -0.00935495924204588,
        0.44607970118522644,
        0.03148791193962097,
        0.8943902850151062
      ],
      "can_relative_orientation_from_partial_start_rad": 0.6267660798013596,
      "can_relative_translation_from_partial_start_m": [
        -0.0018497556447982788,
        -0.06884926557540894,
        -0.028325259685516357
      ],
      "can_to_box_relative_orientation_rad": 1.642514486230046,
      "finger_contact": {
        "evidence_complete": true,
        "pair_count": 1,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.813018321990967,
        -6.813075065612793
      ],
      "left_finger_qvel_mps": [
        -0.001709847478196025,
        0.0012472679372876883
      ],
      "linear_speed_mps": 1.115615086806369,
      "local_corner_max_m": [
        0.04796781169841527,
        0.1443961368663259,
        0.019980366983326225
      ],
      "local_corner_min_m": [
        -0.053354841584030255,
        0.04862142322231022,
        -0.07556930190271333
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.05043650983713566,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.09821134428015543,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.002661675394115881,
      "step_index": 2213,
      "timestamp_seconds": 8.852000420447439,
      "trace_row": 2213,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.03963074155282455,
      "vertical_lower_margin_m": 0.026856027908808863,
      "vertical_upper_margin_m": -0.03963074155282455
    },
    {
      "actual_left_finger_qpos_m": [
        0.022847628220915794,
        0.02243727445602417
      ],
      "angular_speed_rps": 4.832251170668743,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002758505782839815,
        0.09196584062392887,
        -0.028689952471183056
      ],
      "can_pose": [
        -0.32073476910591125,
        -0.15528759360313416,
        0.8697296380996704,
        -0.009275554679334164,
        0.4374215006828308,
        0.031141292303800583,
        0.898669421672821
      ],
      "can_relative_orientation_from_partial_start_rad": 0.646064138751955,
      "can_relative_translation_from_partial_start_m": [
        -0.0019125789403915405,
        -0.07338553667068481,
        -0.02917817234992981
      ],
      "can_to_box_relative_orientation_rad": 1.648852526307334,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812923431396484,
        -6.8129754066467285
      ],
      "left_finger_qvel_mps": [
        -0.001871566055342555,
        0.0014426343841478229
      ],
      "linear_speed_mps": 1.1540461484804192,
      "local_corner_max_m": [
        0.04786039414385673,
        0.13996552582670096,
        0.01915589958100744
      ],
      "local_corner_min_m": [
        -0.05337740570953636,
        0.04396615542115678,
        -0.07653580452337355
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04954102482564615,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.09738687687783665,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.0016951727734556554,
      "step_index": 2214,
      "timestamp_seconds": 8.856000420637429,
      "trace_row": 2214,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.035200130513199604,
      "vertical_lower_margin_m": 0.022200760107655423,
      "vertical_upper_margin_m": -0.035200130513199604
    },
    {
      "actual_left_finger_qpos_m": [
        0.022846145555377007,
        0.022437766194343567
      ],
      "angular_speed_rps": 4.831284981654549,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002823481300963715,
        0.08726613552370388,
        -0.02958540889147293
      ],
      "can_pose": [
        -0.3215877115726471,
        -0.1553504317998886,
        0.8650368452072144,
        -0.009191878139972687,
        0.4287240207195282,
        0.030796930193901062,
        0.9028638005256653
      ],
      "can_relative_orientation_from_partial_start_rad": 0.6653595623827409,
      "can_relative_translation_from_partial_start_m": [
        -0.001975417137145996,
        -0.07807832956314087,
        -0.03003111481666565
      ],
      "can_to_box_relative_orientation_rad": 1.6553317466748536,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812809467315674,
        -6.81287145614624
      ],
      "left_finger_qvel_mps": [
        -0.001627627876587212,
        0.0012392819626256824
      ],
      "linear_speed_mps": 1.1925226009526857,
      "local_corner_max_m": [
        0.04775339790609931,
        0.1353607715356,
        0.018314419408253402
      ],
      "local_corner_min_m": [
        -0.05340036050802677,
        0.03917149951180776,
        -0.07748523719119926
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.048645568405356276,
      "opening_projection_inside": true,
      "opening_projection_overlap_signed_m": 0.09654539670508261,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": 0.000745740105629944,
      "step_index": 2215,
      "timestamp_seconds": 8.860000420827419,
      "trace_row": 2215,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.03059537622209864,
      "vertical_lower_margin_m": 0.0174061041983064,
      "vertical_upper_margin_m": -0.03059537622209864
    },
    {
      "actual_left_finger_qpos_m": [
        0.02284478396177292,
        0.022438131272792816
      ],
      "angular_speed_rps": 4.830291718962374,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0028884563093944937,
        0.08240912978302839,
        -0.03048083492682635
      ],
      "can_pose": [
        -0.3224406838417053,
        -0.15541329979896545,
        0.8601869940757751,
        -0.009103957563638687,
        0.41998809576034546,
        0.03045487590134144,
        0.9069729447364807
      ],
      "can_relative_orientation_from_partial_start_rad": 0.6846521304416309,
      "can_relative_translation_from_partial_start_m": [
        -0.0020382851362228394,
        -0.08292818069458008,
        -0.030884087085723877
      ],
      "can_to_box_relative_orientation_rad": 1.661950215463311,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812727928161621,
        -6.812775611877441
      ],
      "left_finger_qvel_mps": [
        -0.0016454393044114113,
        0.001238659373484552
      ],
      "linear_speed_mps": 1.231172402893429,
      "local_corner_max_m": [
        0.047646830005967145,
        0.130581312314901,
        0.01745590254935364
      ],
      "local_corner_min_m": [
        -0.05342374262475613,
        0.03423694725115578,
        -0.07841757240300634
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04775014237000286,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.09568687984618285,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.00018659510617713426,
      "step_index": 2216,
      "timestamp_seconds": 8.864000421017408,
      "trace_row": 2216,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.025815917001399638,
      "vertical_lower_margin_m": 0.01247155193765442,
      "vertical_upper_margin_m": -0.025815917001399638
    },
    {
      "actual_left_finger_qpos_m": [
        0.022843224927783012,
        0.022438593208789825
      ],
      "angular_speed_rps": 4.829323883826878,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.002953445697429141,
        0.07739536035067496,
        -0.03137625928710486
      ],
      "can_pose": [
        -0.3232937157154083,
        -0.15547621250152588,
        0.8551806211471558,
        -0.009011823683977127,
        0.41121453046798706,
        0.030115170404314995,
        0.9109965562820435
      ],
      "can_relative_orientation_from_partial_start_rad": 0.703941844889185,
      "can_relative_translation_from_partial_start_m": [
        -0.002101197838783264,
        -0.08793455362319946,
        -0.03173711895942688
      ],
      "can_to_box_relative_orientation_rad": 1.6687060780430063,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.81262731552124,
        -6.81268835067749
      ],
      "left_finger_qvel_mps": [
        -0.0017185240285471082,
        0.00129098875913769
      ],
      "linear_speed_mps": 1.2697290270880446,
      "local_corner_max_m": [
        0.04754069565389912,
        0.12562766492555277,
        0.016580301302217992
      ],
      "local_corner_min_m": [
        -0.053447587048757406,
        0.029163055775797142,
        -0.07933281987642771
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04685471800972435,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.0948112785990472,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.0011018425795984998,
      "step_index": 2217,
      "timestamp_seconds": 8.868000421207398,
      "trace_row": 2217,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020862269612051412,
      "vertical_lower_margin_m": 0.007397660462295782,
      "vertical_upper_margin_m": -0.020862269612051412
    },
    {
      "actual_left_finger_qpos_m": [
        0.02284175157546997,
        0.022439025342464447
      ],
      "angular_speed_rps": 4.828351695714066,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.003018419623681684,
        0.07222482812398556,
        -0.03227168064493019
      ],
      "can_pose": [
        -0.3241468071937561,
        -0.1555391401052475,
        0.8500177264213562,
        -0.008915507234632969,
        0.40240421891212463,
        0.02977786213159561,
        0.9149343967437744
      ],
      "can_relative_orientation_from_partial_start_rad": 0.7232285988757289,
      "can_relative_translation_from_partial_start_m": [
        -0.002164125442504883,
        -0.09309744834899902,
        -0.03259021043777466
      ],
      "can_to_box_relative_orientation_rad": 1.6755974261445823,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812527656555176,
        -6.812578201293945
      ],
      "left_finger_qvel_mps": [
        -0.0017260246677324176,
        0.0013108213897794485
      ],
      "linear_speed_mps": 1.3083196355866127,
      "local_corner_max_m": [
        0.047435044920841135,
        0.1204998162878308,
        0.015687604103051145
      ],
      "local_corner_min_m": [
        -0.05347188416820453,
        0.02394983996014033,
        -0.08023096539291152
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04595929665189902,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.09391858139988035,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.001999988096082317,
      "step_index": 2218,
      "timestamp_seconds": 8.872000421397388,
      "trace_row": 2218,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.015734420974329436,
      "vertical_lower_margin_m": 0.0021844446466389687,
      "vertical_upper_margin_m": -0.015734420974329436
    },
    {
      "actual_left_finger_qpos_m": [
        0.02284041978418827,
        0.02243940345942974
      ],
      "angular_speed_rps": 4.827378759936691,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0030833929847079167,
        0.06689693735844582,
        -0.03316706801422842
      ],
      "can_pose": [
        -0.32499992847442627,
        -0.1556020975112915,
        0.8446977138519287,
        -0.008815038949251175,
        0.39355796575546265,
        0.029442986473441124,
        0.9187860488891602
      ],
      "can_relative_orientation_from_partial_start_rad": 0.7425123093468753,
      "can_relative_translation_from_partial_start_m": [
        -0.002227082848548889,
        -0.09841746091842651,
        -0.033443331718444824
      ],
      "can_to_box_relative_orientation_rad": 1.6826223606257131,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812427043914795,
        -6.812486171722412
      ],
      "left_finger_qvel_mps": [
        -0.001628420315682888,
        0.0012514700647443533
      ],
      "linear_speed_mps": 1.3470873796654537,
      "local_corner_max_m": [
        0.047329882114291955,
        0.1151971626292877,
        0.01477783542719524
      ],
      "local_corner_min_m": [
        -0.05349666808370779,
        0.01859671208760394,
        -0.08111197145565208
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04506390928260079,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.09300881272402445,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.0028809941588228694,
      "step_index": 2219,
      "timestamp_seconds": 8.876000421587378,
      "trace_row": 2219,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.010431767315786336,
      "vertical_lower_margin_m": -0.003168683225897421,
      "vertical_upper_margin_m": -0.010431767315786336
    },
    {
      "actual_left_finger_qpos_m": [
        0.02283891662955284,
        0.022439906373620033
      ],
      "angular_speed_rps": 4.826413515403776,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0031483657459331627,
        0.06141234465147205,
        -0.03406244999567759
      ],
      "can_pose": [
        -0.3258531093597412,
        -0.1556650847196579,
        0.8392212390899658,
        -0.008710449561476707,
        0.38467663526535034,
        0.029110589995980263,
        0.9225512742996216
      ],
      "can_relative_orientation_from_partial_start_rad": 0.7617929344616857,
      "can_relative_translation_from_partial_start_m": [
        -0.002290070056915283,
        -0.1038939356803894,
        -0.034296512603759766
      ],
      "can_to_box_relative_orientation_rad": 1.6897789798574123,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812328815460205,
        -6.812379360198975
      ],
      "left_finger_qvel_mps": [
        -0.0015248565468937159,
        0.0011302637867629528
      ],
      "linear_speed_mps": 1.385723139540104,
      "local_corner_max_m": [
        0.04722522655171185,
        0.10972035960749327,
        0.01385096663560631
      ],
      "local_corner_min_m": [
        -0.05352195804357818,
        0.013104329695450834,
        -0.08197586662696149
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04416852730115162,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.09208194393243552,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.003744889330132284,
      "step_index": 2220,
      "timestamp_seconds": 8.880000421777368,
      "trace_row": 2220,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.008661065618050526,
      "vertical_lower_margin_m": -0.008661065618050526,
      "vertical_upper_margin_m": -0.004954964293991906
    },
    {
      "actual_left_finger_qpos_m": [
        0.022837547585368156,
        0.022440362721681595
      ],
      "angular_speed_rps": 4.825401597002427,
      "box_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.003213337888981732,
        0.055770931378445576,
        -0.034957795547654436
      ],
      "can_pose": [
        -0.32670632004737854,
        -0.15572810173034668,
        0.833588182926178,
        -0.008601768873631954,
        0.3757611811161041,
        0.02878071554005146,
        0.9262297749519348
      ],
      "can_relative_orientation_from_partial_start_rad": 0.7810702221032086,
      "can_relative_translation_from_partial_start_m": [
        -0.002353087067604065,
        -0.10952699184417725,
        -0.035149723291397095
      ],
      "can_to_box_relative_orientation_rad": 1.6970653024947018,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812242031097412,
        -6.812286376953125
      ],
      "left_finger_qvel_mps": [
        -0.0014405944384634495,
        0.0011035887291654944
      ],
      "linear_speed_mps": 1.4244134380877358,
      "local_corner_max_m": [
        0.04712109711187723,
        0.10406929374396201,
        0.012907035270558975
      ],
      "local_corner_min_m": [
        -0.053547772889840695,
        0.007472569012929142,
        -0.08282262636586785
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04327318174917477,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.09113801256738818,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.004591649069038639,
      "step_index": 2221,
      "timestamp_seconds": 8.884000421967357,
      "trace_row": 2221,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.014292826300572218,
      "vertical_lower_margin_m": -0.014292826300572218,
      "vertical_upper_margin_m": 0.0006961015695393508
    },
    {
      "actual_left_finger_qpos_m": [
        0.02283593825995922,
        0.02244085818529129
      ],
      "angular_speed_rps": 4.824447411124056,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 2,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0032783093657525186,
        0.049972221973660025,
        -0.035853133257009895
      ],
      "can_pose": [
        -0.32755959033966064,
        -0.15579114854335785,
        0.827798068523407,
        -0.008489027619361877,
        0.36681225895881653,
        0.02845340222120285,
        0.9298210740089417
      ],
      "can_relative_orientation_from_partial_start_rad": 0.8003443434522381,
      "can_relative_translation_from_partial_start_m": [
        -0.0024161338806152344,
        -0.11531710624694824,
        -0.0360029935836792
      ],
      "can_to_box_relative_orientation_rad": 1.7044794952300935,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812145709991455,
        -6.812190532684326
      ],
      "left_finger_qvel_mps": [
        -0.0016438920283690095,
        0.0011973022483289242
      ],
      "linear_speed_mps": 1.463246959573413,
      "local_corner_max_m": [
        0.047017512143369744,
        0.0982435017797596,
        0.01194602559042246
      ],
      "local_corner_min_m": [
        -0.05357413087487478,
        0.0017009421675604486,
        -0.08365229210444225
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04237784403981931,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.09017700288725167,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.005421314807613042,
      "step_index": 2222,
      "timestamp_seconds": 8.888000422157347,
      "trace_row": 2222,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02006445314594091,
      "vertical_lower_margin_m": -0.02006445314594091,
      "vertical_upper_margin_m": 0.00652189353374176
    },
    {
      "actual_left_finger_qpos_m": [
        0.022834481671452522,
        0.022441312670707703
      ],
      "angular_speed_rps": 4.823484545357212,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 8,
        "physical_hit": false
      },
      "can_geometry_center_box_local_m": [
        -0.0033432801946580715,
        0.044016752903143774,
        -0.03674846214625288
      ],
      "can_pose": [
        -0.3284129202365875,
        -0.1558542251586914,
        0.8218514323234558,
        -0.008372261188924313,
        0.35783088207244873,
        0.028128694742918015,
        0.9333252310752869
      ],
      "can_relative_orientation_from_partial_start_rad": 0.8196152100412428,
      "can_relative_translation_from_partial_start_m": [
        -0.0024792104959487915,
        -0.12126374244689941,
        -0.03685632348060608
      ],
      "can_to_box_relative_orientation_rad": 1.7120196440746656,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.812058448791504,
        -6.812106132507324
      ],
      "left_finger_qvel_mps": [
        -0.0017080896068364382,
        0.0013138777576386929
      ],
      "linear_speed_mps": 1.5019701486330175,
      "local_corner_max_m": [
        0.046914488780382624,
        0.09224353747632341,
        0.010967957465490119
      ],
      "local_corner_min_m": [
        -0.05360104916969877,
        -0.004210031670035863,
        -0.08446488175799588
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04148251515057633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08919893476231933,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.006233904461166673,
      "step_index": 2223,
      "timestamp_seconds": 8.892000422347337,
      "trace_row": 2223,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.025975426983537223,
      "vertical_lower_margin_m": -0.025975426983537223,
      "vertical_upper_margin_m": 0.01252185783717795
    },
    {
      "actual_left_finger_qpos_m": [
        0.022833172231912613,
        0.022441724315285683
      ],
      "angular_speed_rps": 9.336383878425206,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 12,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0040719867962910605,
        0.040193695997361556,
        -0.037481935769014485
      ],
      "can_pose": [
        -0.32898804545402527,
        -0.15653489530086517,
        0.8194025754928589,
        -0.012134292162954807,
        0.34716999530792236,
        0.013901843689382076,
        0.9376207590103149
      ],
      "can_relative_orientation_from_partial_start_rad": 0.8446784998200342,
      "can_relative_translation_from_partial_start_m": [
        -0.0031598806381225586,
        -0.12371259927749634,
        -0.03743144869804382
      ],
      "can_to_box_relative_orientation_rad": 1.7440457423927005,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811957359313965,
        -6.812011241912842
      ],
      "left_finger_qvel_mps": [
        -0.0017332693096250296,
        0.0013982836389914155
      ],
      "linear_speed_mps": 0.6514877200412329,
      "local_corner_max_m": [
        0.04573246576046097,
        0.08700123971952745,
        0.010008990769198478
      ],
      "local_corner_min_m": [
        -0.05387643935304309,
        -0.006613847724804334,
        -0.08497286230722745
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04074904152781472,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08823996806602769,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.006741885010398241,
      "step_index": 2224,
      "timestamp_seconds": 8.896000422537327,
      "trace_row": 2224,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.028379243038305694,
      "vertical_lower_margin_m": -0.028379243038305694,
      "vertical_upper_margin_m": 0.017764155593973915
    },
    {
      "actual_left_finger_qpos_m": [
        0.02283177152276039,
        0.022442251443862915
      ],
      "angular_speed_rps": 9.968249636660413,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 17,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004847206672264209,
        0.04002930643864444,
        -0.038059714005099665
      ],
      "can_pose": [
        -0.3294793963432312,
        -0.15730497241020203,
        0.8206535577774048,
        -0.01642666757106781,
        0.3349478542804718,
        -0.0005771216237917542,
        0.9420934915542603
      ],
      "can_relative_orientation_from_partial_start_rad": 0.8737064292066417,
      "can_relative_translation_from_partial_start_m": [
        -0.003929957747459412,
        -0.12246161699295044,
        -0.037922799587249756
      ],
      "can_to_box_relative_orientation_rad": 1.7784381779489167,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811847686767578,
        -6.811903953552246
      ],
      "left_finger_qvel_mps": [
        -0.0015913316747173667,
        0.0012465904001146555
      ],
      "linear_speed_mps": 0.38724999184674613,
      "local_corner_max_m": [
        0.04475524744890064,
        0.08646563047826372,
        0.009238191248129302
      ],
      "local_corner_min_m": [
        -0.054449660793429056,
        -0.00640701760097484,
        -0.08535761925832863
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.04017126329172954,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08746916854495851,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.007126641961499425,
      "step_index": 2225,
      "timestamp_seconds": 8.900000422727317,
      "trace_row": 2225,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0281724129144762,
      "vertical_lower_margin_m": -0.0281724129144762,
      "vertical_upper_margin_m": 0.01829976483523764
    },
    {
      "actual_left_finger_qpos_m": [
        0.022830404341220856,
        0.022442694753408432
      ],
      "angular_speed_rps": 8.088363100827937,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 18,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.005355239731175965,
        0.040620610520241685,
        -0.038641777828496426
      ],
      "can_pose": [
        -0.33002427220344543,
        -0.15783244371414185,
        0.8221508860588074,
        -0.019108643755316734,
        0.32271021604537964,
        -0.009927364997565746,
        0.9462529420852661
      ],
      "can_relative_orientation_from_partial_start_rad": 0.9018140197965124,
      "can_relative_translation_from_partial_start_m": [
        -0.004457429051399231,
        -0.12096428871154785,
        -0.03846767544746399
      ],
      "can_to_box_relative_orientation_rad": 1.8042002593102018,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811764717102051,
        -6.811817169189453
      ],
      "left_finger_qvel_mps": [
        -0.0017395869363099337,
        0.0013787606731057167
      ],
      "linear_speed_mps": 0.41960602013982656,
      "local_corner_max_m": [
        0.044481064687017124,
        0.08782000370343557,
        0.008481490455876817
      ],
      "local_corner_min_m": [
        -0.055191544149369054,
        -0.006578782662952198,
        -0.08576504611286967
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03958919946833278,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08671246775270602,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.007534068816040462,
      "step_index": 2226,
      "timestamp_seconds": 8.904000422917306,
      "trace_row": 2226,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02834417797645356,
      "vertical_lower_margin_m": -0.02834417797645356,
      "vertical_upper_margin_m": 0.016945391610065794
    },
    {
      "actual_left_finger_qpos_m": [
        0.022829145193099976,
        0.022443093359470367
      ],
      "angular_speed_rps": 7.9012735351392385,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 18,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.005832773834430205,
        0.041174665088112405,
        -0.03922520011524383
      ],
      "can_pose": [
        -0.3305814564228058,
        -0.15834392607212067,
        0.8235493302345276,
        -0.021461278200149536,
        0.31038898229599,
        -0.018697699531912804,
        0.9501834511756897
      ],
      "can_relative_orientation_from_partial_start_rad": 0.9299912917122204,
      "can_relative_translation_from_partial_start_m": [
        -0.004968911409378052,
        -0.11956584453582764,
        -0.03902485966682434
      ],
      "can_to_box_relative_orientation_rad": 1.828949721999742,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811656475067139,
        -6.811712741851807
      ],
      "left_finger_qvel_mps": [
        -0.0016729396302253008,
        0.0013391906395554543
      ],
      "linear_speed_mps": 0.3974696788210381,
      "local_corner_max_m": [
        0.044803903534429174,
        0.08903000963199548,
        0.007703971993344327
      ],
      "local_corner_min_m": [
        -0.05646945120328961,
        -0.006680679455770666,
        -0.08615437222383199
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03900577718158538,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08593494929017353,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.00792339492700278,
      "step_index": 2227,
      "timestamp_seconds": 8.908000423107296,
      "trace_row": 2227,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.028446074769272026,
      "vertical_lower_margin_m": -0.028446074769272026,
      "vertical_upper_margin_m": 0.015735385681505884
    },
    {
      "actual_left_finger_qpos_m": [
        0.022827742621302605,
        0.02244349755346775
      ],
      "angular_speed_rps": 7.7505939188626245,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 18,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.006290232420100517,
        0.04166342197027828,
        -0.039812923926664356
      ],
      "can_pose": [
        -0.33115288615226746,
        -0.15884748101234436,
        0.8248350024223328,
        -0.023543694987893105,
        0.298024445772171,
        -0.027026046067476273,
        0.9538851380348206
      ],
      "can_relative_orientation_from_partial_start_rad": 0.9581442262840613,
      "can_relative_translation_from_partial_start_m": [
        -0.005472466349601746,
        -0.11828017234802246,
        -0.03959628939628601
      ],
      "can_to_box_relative_orientation_rad": 1.852915210974603,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.81156063079834,
        -6.8116135597229
      ],
      "left_finger_qvel_mps": [
        -0.0016971409786492586,
        0.0012885386822745204
      ],
      "linear_speed_mps": 0.3735850201011381,
      "local_corner_max_m": [
        0.04508148804409523,
        0.09008501498045629,
        0.006902314316447555
      ],
      "local_corner_min_m": [
        -0.057661952884296264,
        -0.00675817103989973,
        -0.08652816216977627
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03841805337016485,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08513329161327676,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.008297184872947061,
      "step_index": 2228,
      "timestamp_seconds": 8.912000423297286,
      "trace_row": 2228,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02852356635340109,
      "vertical_lower_margin_m": -0.02852356635340109,
      "vertical_upper_margin_m": 0.01468038033304507
    },
    {
      "actual_left_finger_qpos_m": [
        0.022826315835118294,
        0.022443944588303566
      ],
      "angular_speed_rps": 7.422649720908718,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 18,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0067014115893273,
        0.04219613172583059,
        -0.04040576286599923
      ],
      "can_pose": [
        -0.33174312114715576,
        -0.1593102663755417,
        0.8260639309883118,
        -0.02525501139461994,
        0.2857119143009186,
        -0.034356217831373215,
        0.9573665857315063
      ],
      "can_relative_orientation_from_partial_start_rad": 0.9858624122198074,
      "can_relative_translation_from_partial_start_m": [
        -0.005935251712799072,
        -0.11705124378204346,
        -0.040186524391174316
      ],
      "can_to_box_relative_orientation_rad": 1.8751774242875447,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811450004577637,
        -6.811500072479248
      ],
      "left_finger_qvel_mps": [
        -0.0016940697096288204,
        0.001298996969126165
      ],
      "linear_speed_mps": 0.35993166581945013,
      "local_corner_max_m": [
        0.04529665905881078,
        0.09104881896626071,
        0.006081187259817433
      ],
      "local_corner_min_m": [
        -0.05869948223746535,
        -0.006656555514599538,
        -0.08689271299181589
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03782521443082998,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08431216455664664,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.008661735694986683,
      "step_index": 2229,
      "timestamp_seconds": 8.916000423487276,
      "trace_row": 2229,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.028421950828100898,
      "vertical_lower_margin_m": -0.028421950828100898,
      "vertical_upper_margin_m": 0.013716576347240647
    },
    {
      "actual_left_finger_qpos_m": [
        0.02282484620809555,
        0.02244430221617222
      ],
      "angular_speed_rps": 7.352385906325243,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 19,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0071054118060879246,
        0.042612211866195016,
        -0.0410018885290262
      ],
      "can_pose": [
        -0.33234524726867676,
        -0.15977439284324646,
        0.8271552324295044,
        -0.026812491938471794,
        0.27338075637817383,
        -0.041501376777887344,
        0.9606361389160156
      ],
      "can_relative_orientation_from_partial_start_rad": 1.0135209073407287,
      "can_relative_translation_from_partial_start_m": [
        -0.006399378180503845,
        -0.11595994234085083,
        -0.04078865051269531
      ],
      "can_to_box_relative_orientation_rad": 1.8971257129942185,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811349868774414,
        -6.811404228210449
      ],
      "left_finger_qvel_mps": [
        -0.0017792690778151155,
        0.0013247668975964189
      ],
      "linear_speed_mps": 0.3325007435850607,
      "local_corner_max_m": [
        0.045482729127949095,
        0.09183818515981468,
        0.005236931441432002
      ],
      "local_corner_min_m": [
        -0.059693552740124944,
        -0.006613761427424647,
        -0.0872407084994844
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03722908876780301,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08346790873826121,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.009009731202655191,
      "step_index": 2230,
      "timestamp_seconds": 8.920000423677266,
      "trace_row": 2230,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.028379156740926007,
      "vertical_lower_margin_m": -0.028379156740926007,
      "vertical_upper_margin_m": 0.012927210153686683
    },
    {
      "actual_left_finger_qpos_m": [
        0.022823510691523552,
        0.02244466543197632
      ],
      "angular_speed_rps": 7.180743918819536,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 20,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.007484513835107176,
        0.04299111450088278,
        -0.04160453696092975
      ],
      "can_pose": [
        -0.3329637944698334,
        -0.1602170765399933,
        0.828149676322937,
        -0.028131598606705666,
        0.2610526382923126,
        -0.04806146025657654,
        0.963716983795166
      ],
      "can_relative_orientation_from_partial_start_rad": 1.0409269917392674,
      "can_relative_translation_from_partial_start_m": [
        -0.006842061877250671,
        -0.11496549844741821,
        -0.04140719771385193
      ],
      "can_to_box_relative_orientation_rad": 1.9181237798943787,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811234474182129,
        -6.811291694641113
      ],
      "left_finger_qvel_mps": [
        -0.0015196679159998894,
        0.0011327287647873163
      ],
      "linear_speed_mps": 0.3129984029218608,
      "local_corner_max_m": [
        0.045626302854494816,
        0.09249902051039682,
        0.0043681820024903395
      ],
      "local_corner_min_m": [
        -0.06059533052470917,
        -0.00651679150863127,
        -0.08757725592434984
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03662644033589946,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08259915929931955,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.009346278627520632,
      "step_index": 2231,
      "timestamp_seconds": 8.924000423867255,
      "trace_row": 2231,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02828218682213263,
      "vertical_lower_margin_m": -0.02828218682213263,
      "vertical_upper_margin_m": 0.012266374803104538
    },
    {
      "actual_left_finger_qpos_m": [
        0.022822272032499313,
        0.022444985806941986
      ],
      "angular_speed_rps": 7.086979482414149,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 20,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.007848243129122301,
        0.04328895506186592,
        -0.04221178748089205
      ],
      "can_pose": [
        -0.3335949182510376,
        -0.1606481671333313,
        0.8290255665779114,
        -0.029273036867380142,
        0.2486945539712906,
        -0.054262924939394,
        0.96661776304245
      ],
      "can_relative_orientation_from_partial_start_rad": 1.0682114890802599,
      "can_relative_translation_from_partial_start_m": [
        -0.007273152470588684,
        -0.11408960819244385,
        -0.04203832149505615
      ],
      "can_to_box_relative_orientation_rad": 1.9385726075288727,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811147212982178,
        -6.811197757720947
      ],
      "left_finger_qvel_mps": [
        -0.0016466024098917842,
        0.0013086479157209396
      ],
      "linear_speed_mps": 0.2906178695098048,
      "local_corner_max_m": [
        0.045738381240254644,
        0.09300928462129743,
        0.003474587010828978
      ],
      "local_corner_min_m": [
        -0.061434867498499246,
        -0.0064313744975655895,
        -0.08789816197261308
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03601918981593716,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08170556430765819,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.009667184675783869,
      "step_index": 2232,
      "timestamp_seconds": 8.928000424057245,
      "trace_row": 2232,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02819676981106695,
      "vertical_lower_margin_m": -0.02819676981106695,
      "vertical_upper_margin_m": 0.011756110692203933
    },
    {
      "actual_left_finger_qpos_m": [
        0.02282104454934597,
        0.022445369511842728
      ],
      "angular_speed_rps": 7.0123637030192105,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 21,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008164672453785188,
        0.043599769944675515,
        -0.042818808242504836
      ],
      "can_pose": [
        -0.33423474431037903,
        -0.16102856397628784,
        0.8298328518867493,
        -0.03013552539050579,
        0.23608605563640594,
        -0.059653300791978836,
        0.9694312214851379
      ],
      "can_relative_orientation_from_partial_start_rad": 1.0956437160104742,
      "can_relative_translation_from_partial_start_m": [
        -0.007653549313545227,
        -0.11328232288360596,
        -0.04267814755439758
      ],
      "can_to_box_relative_orientation_rad": 1.9579725078392438,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.811044216156006,
        -6.811097145080566
      ],
      "left_finger_qvel_mps": [
        -0.001738118240609765,
        0.0014113058568909764
      ],
      "linear_speed_mps": 0.2745210146402052,
      "local_corner_max_m": [
        0.0458176678389835,
        0.09341881798530183,
        0.0025553506462723252
      ],
      "local_corner_min_m": [
        -0.062147012746553876,
        -0.006219278095950798,
        -0.088192967131282
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03541216905432437,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.08078632794310153,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.009961989834452789,
      "step_index": 2233,
      "timestamp_seconds": 8.932000424247235,
      "trace_row": 2233,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.027984673409452158,
      "vertical_lower_margin_m": -0.027984673409452158,
      "vertical_upper_margin_m": 0.011346577328199534
    },
    {
      "actual_left_finger_qpos_m": [
        0.022819917649030685,
        0.022445688024163246
      ],
      "angular_speed_rps": 6.791156347860911,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 22,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008422763323515242,
        0.043958593237267474,
        -0.04342224011572071
      ],
      "can_pose": [
        -0.33487725257873535,
        -0.16134235262870789,
        0.8305908441543579,
        -0.030702536925673485,
        0.22353215515613556,
        -0.06405866146087646,
        0.9721046686172485
      ],
      "can_relative_orientation_from_partial_start_rad": 1.1225288941189024,
      "can_relative_translation_from_partial_start_m": [
        -0.007967337965965271,
        -0.11252433061599731,
        -0.043320655822753906
      ],
      "can_to_box_relative_orientation_rad": 1.9758157277159303,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.810934066772461,
        -6.810988426208496
      ],
      "left_finger_qvel_mps": [
        -0.0014829740393906832,
        0.0011673232074826956
      ],
      "linear_speed_mps": 0.2605082013943824,
      "local_corner_max_m": [
        0.04586647013565495,
        0.09375919568880176,
        0.0016190362098116307
      ],
      "local_corner_min_m": [
        -0.06271199678268541,
        -0.005842009214266808,
        -0.08846351644125305
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.034808737181108496,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07985001350664084,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.010232539144423847,
      "step_index": 2234,
      "timestamp_seconds": 8.936000424437225,
      "trace_row": 2234,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.027607404527768168,
      "vertical_lower_margin_m": -0.027607404527768168,
      "vertical_upper_margin_m": 0.011006199624699606
    },
    {
      "actual_left_finger_qpos_m": [
        0.022818641737103462,
        0.022446105256676674
      ],
      "angular_speed_rps": 6.737790953789049,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 26,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008659764407474707,
        0.044223937333988994,
        -0.04402725404374147
      ],
      "can_pose": [
        -0.3355240821838379,
        -0.1616343855857849,
        0.8312269449234009,
        -0.03112729825079441,
        0.21096141636371613,
        -0.06819114089012146,
        0.9746161103248596
      ],
      "can_relative_orientation_from_partial_start_rad": 1.1492705733236408,
      "can_relative_translation_from_partial_start_m": [
        -0.008259370923042297,
        -0.11188822984695435,
        -0.043967485427856445
      ],
      "can_to_box_relative_orientation_rad": 1.993273115463614,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.81083869934082,
        -6.810891151428223
      ],
      "left_finger_qvel_mps": [
        -0.0015542979817837477,
        0.001222164137288928
      ],
      "linear_speed_mps": 0.23826139638926952,
      "local_corner_max_m": [
        0.04590320981486537,
        0.09395028172038389,
        0.0006558439859627452
      ],
      "local_corner_min_m": [
        -0.06322273862981476,
        -0.0055024070524059,
        -0.08871035207344569
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03420372325308774,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07888682128279195,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.010479374776616479,
      "step_index": 2235,
      "timestamp_seconds": 8.940000424627215,
      "trace_row": 2235,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02726780236590726,
      "vertical_lower_margin_m": -0.02726780236590726,
      "vertical_upper_margin_m": 0.010815113593117473
    },
    {
      "actual_left_finger_qpos_m": [
        0.02281719073653221,
        0.022446487098932266
      ],
      "angular_speed_rps": 6.650497727968753,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 25,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008863063869344046,
        0.044453204313259276,
        -0.0446348824959234
      ],
      "can_pose": [
        -0.33617615699768066,
        -0.1618870347738266,
        0.8317707180976868,
        -0.03135982155799866,
        0.19837228953838348,
        -0.07175801694393158,
        0.9769933223724365
      ],
      "can_relative_orientation_from_partial_start_rad": 1.1757654513872067,
      "can_relative_translation_from_partial_start_m": [
        -0.008512020111083984,
        -0.11134445667266846,
        -0.04461956024169922
      ],
      "can_to_box_relative_orientation_rad": 2.0099155913853304,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.810741901397705,
        -6.810789585113525
      ],
      "left_finger_qvel_mps": [
        -0.0015167755773290992,
        0.0011158097768202424
      ],
      "linear_speed_mps": 0.22146139132963677,
      "local_corner_max_m": [
        0.04592071743023987,
        0.09402597819051861,
        -0.0003355063918288881
      ],
      "local_corner_min_m": [
        -0.06364684516892793,
        -0.005119569564000059,
        -0.08893425860001791
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03359609480090581,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07789547090500032,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.010703281303188705,
      "step_index": 2236,
      "timestamp_seconds": 8.944000424817204,
      "trace_row": 2236,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02688496487750142,
      "vertical_lower_margin_m": -0.02688496487750142,
      "vertical_upper_margin_m": 0.01073941712298275
    },
    {
      "actual_left_finger_qpos_m": [
        0.022815987467765808,
        0.022446874529123306
      ],
      "angular_speed_rps": 6.6189678168832735,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 25,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00906858383689016,
        0.04456206534384166,
        -0.04524403342970229
      ],
      "can_pose": [
        -0.3368315100669861,
        -0.16214029490947723,
        0.8321702480316162,
        -0.031477056443691254,
        0.18575626611709595,
        -0.07509265094995499,
        0.9792165756225586
      ],
      "can_relative_orientation_from_partial_start_rad": 1.2021590055566547,
      "can_relative_translation_from_partial_start_m": [
        -0.00876528024673462,
        -0.11094492673873901,
        -0.04527491331100464
      ],
      "can_to_box_relative_orientation_rad": 2.026274197996995,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.810652732849121,
        -6.810699939727783
      ],
      "left_finger_qvel_mps": [
        -0.0015782307600602508,
        0.001271347515285015
      ],
      "linear_speed_mps": 0.20206008509349138,
      "local_corner_max_m": [
        0.045908575470073404,
        0.09393114981693418,
        -0.0013545534770325607
      ],
      "local_corner_min_m": [
        -0.06404574314385375,
        -0.004807019129250856,
        -0.08913351338237202
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03298694386712692,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07687642381979665,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.010902536085542813,
      "step_index": 2237,
      "timestamp_seconds": 8.948000425007194,
      "trace_row": 2237,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.026572414442752216,
      "vertical_lower_margin_m": -0.026572414442752216,
      "vertical_upper_margin_m": 0.010834245496567182
    },
    {
      "actual_left_finger_qpos_m": [
        0.02281479351222515,
        0.022447172552347183
      ],
      "angular_speed_rps": 6.584409061300961,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 26,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009229786488099578,
        0.044675907199698495,
        -0.04585697330507987
      ],
      "can_pose": [
        -0.33749061822891235,
        -0.16233870387077332,
        0.8325006365776062,
        -0.03136765584349632,
        0.17302057147026062,
        -0.07767251133918762,
        0.9813495874404907
      ],
      "can_relative_orientation_from_partial_start_rad": 1.228443371646707,
      "can_relative_translation_from_partial_start_m": [
        -0.0089636892080307,
        -0.11061453819274902,
        -0.04593402147293091
      ],
      "can_to_box_relative_orientation_rad": 2.0416448602655852,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.810554027557373,
        -6.810603141784668
      ],
      "left_finger_qvel_mps": [
        -0.0016757443081587553,
        0.001319072674959898
      ],
      "linear_speed_mps": 0.1908772873119132,
      "local_corner_max_m": [
        0.045877298052631965,
        0.09374458558970955,
        -0.0024095457396974274
      ],
      "local_corner_min_m": [
        -0.06433687102883112,
        -0.004392771190312561,
        -0.08930440087046232
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.032374003991749334,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07582143155713178,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011073423573633112,
      "step_index": 2238,
      "timestamp_seconds": 8.952000425197184,
      "trace_row": 2238,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02615816650381392,
      "vertical_lower_margin_m": -0.02615816650381392,
      "vertical_upper_margin_m": 0.01102080972379181
    },
    {
      "actual_left_finger_qpos_m": [
        0.022813668474555016,
        0.022447431460022926
      ],
      "angular_speed_rps": 6.589495359946252,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 28,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009358142654659951,
        0.04475358848156341,
        -0.046474643079607525
      ],
      "can_pose": [
        -0.33815377950668335,
        -0.1624959260225296,
        0.8327399492263794,
        -0.03108626790344715,
        0.16015934944152832,
        -0.07969220727682114,
        0.9833778738975525
      ],
      "can_relative_orientation_from_partial_start_rad": 1.2547101983101001,
      "can_relative_translation_from_partial_start_m": [
        -0.009120911359786987,
        -0.11037522554397583,
        -0.046597182750701904
      ],
      "can_to_box_relative_orientation_rad": 2.056357593813071,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8104472160339355,
        -6.8105034828186035
      ],
      "left_finger_qvel_mps": [
        -0.0016317166155204177,
        0.0013404848286882043
      ],
      "linear_speed_mps": 0.1805844988562972,
      "local_corner_max_m": [
        0.04583132558137351,
        0.09344197628210127,
        -0.0035025563681901906
      ],
      "local_corner_min_m": [
        -0.06454761089069339,
        -0.003934799318974447,
        -0.08944672979102486
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.03175633421722168,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07472842092863902,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011215752494195652,
      "step_index": 2239,
      "timestamp_seconds": 8.956000425387174,
      "trace_row": 2239,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.025700194632475807,
      "vertical_lower_margin_m": -0.025700194632475807,
      "vertical_upper_margin_m": 0.011323419031400092
    },
    {
      "actual_left_finger_qpos_m": [
        0.022812392562627792,
        0.022447718307375908
      ],
      "angular_speed_rps": 6.433622014776569,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 28,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009437404839597041,
        0.04485103988651373,
        -0.04708672819340981
      ],
      "can_pose": [
        -0.3388160169124603,
        -0.1625910848379135,
        0.8329195380210876,
        -0.030697382986545563,
        0.1474931240081787,
        -0.08086945861577988,
        0.9852734804153442
      ],
      "can_relative_orientation_from_partial_start_rad": 1.2802383850352226,
      "can_relative_translation_from_partial_start_m": [
        -0.009216070175170898,
        -0.11019563674926758,
        -0.04725942015647888
      ],
      "can_to_box_relative_orientation_rad": 2.0698281435973103,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.810339450836182,
        -6.810396671295166
      ],
      "left_finger_qvel_mps": [
        -0.0016107900300994515,
        0.0011919299140572548
      ],
      "linear_speed_mps": 0.17318084322382832,
      "local_corner_max_m": [
        0.0457756594458974,
        0.09307170135966836,
        -0.004604563770744252
      ],
      "local_corner_min_m": [
        -0.06465046912509148,
        -0.003369621586640892,
        -0.08956889261607537
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.031144249103419397,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07362641352608496,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011337915319246161,
      "step_index": 2240,
      "timestamp_seconds": 8.960000425577164,
      "trace_row": 2240,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.025135016900142252,
      "vertical_lower_margin_m": -0.025135016900142252,
      "vertical_upper_margin_m": 0.011693693953833004
    },
    {
      "actual_left_finger_qpos_m": [
        0.022803233936429024,
        0.022455420345067978
      ],
      "angular_speed_rps": 6.3602067680564875,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 28,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009481010621825242,
        0.04491960339346923,
        -0.047697510017706723
      ],
      "can_pose": [
        -0.33947882056236267,
        -0.16264091432094574,
        0.8330128788948059,
        -0.030228329822421074,
        0.1349179595708847,
        -0.08144042640924454,
        0.9870415329933167
      ],
      "can_relative_orientation_from_partial_start_rad": 1.3053331523940053,
      "can_relative_translation_from_partial_start_m": [
        -0.009265899658203125,
        -0.11010229587554932,
        -0.047922223806381226
      ],
      "can_to_box_relative_orientation_rad": 2.0824919437754907,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.810240268707275,
        -6.8102946281433105
      ],
      "left_finger_qvel_mps": [
        0.0006265482516027987,
        -0.0013125493424013257
      ],
      "linear_speed_mps": 0.1677990113971956,
      "local_corner_max_m": [
        0.04571354452223522,
        0.09260136946536912,
        -0.005725627726590132
      ],
      "local_corner_min_m": [
        -0.06467556576588573,
        -0.0027621626784306574,
        -0.08966939230882331
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.030533467279122484,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07250534957023907,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011438415011994107,
      "step_index": 2241,
      "timestamp_seconds": 8.964000425767154,
      "trace_row": 2241,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.024527557991932018,
      "vertical_lower_margin_m": -0.024527557991932018,
      "vertical_upper_margin_m": 0.01216402584813224
    },
    {
      "actual_left_finger_qpos_m": [
        0.02280205674469471,
        0.022454651072621346
      ],
      "angular_speed_rps": 6.319772192861476,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 32,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00949061227532702,
        0.044952841759648865,
        -0.04830827245867009
      ],
      "can_pose": [
        -0.34014269709587097,
        -0.16264747083187103,
        0.833016574382782,
        -0.029695063829421997,
        0.12239763140678406,
        -0.08143654465675354,
        0.9886886477470398
      ],
      "can_relative_orientation_from_partial_start_rad": 1.3300915013957044,
      "can_relative_translation_from_partial_start_m": [
        -0.009272456169128418,
        -0.11009860038757324,
        -0.048586100339889526
      ],
      "can_to_box_relative_orientation_rad": 2.094447518841297,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809788703918457,
        -6.809793472290039
      ],
      "left_finger_qvel_mps": [
        -0.0003371171187609434,
        3.9389873563777655e-05
      ],
      "linear_speed_mps": 0.16597979062547352,
      "local_corner_max_m": [
        0.04564709420661078,
        0.09202632967342728,
        -0.006868625046851096
      ],
      "local_corner_min_m": [
        -0.06462831875726482,
        -0.0021206461541295463,
        -0.08974791987048908
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02992270483815912,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07136235224997811,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011516942573659872,
      "step_index": 2242,
      "timestamp_seconds": 8.968000425957143,
      "trace_row": 2242,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.023886041467630906,
      "vertical_lower_margin_m": -0.023886041467630906,
      "vertical_upper_margin_m": 0.012739065640074085
    },
    {
      "actual_left_finger_qpos_m": [
        0.022801151499152184,
        0.02245487831532955
      ],
      "angular_speed_rps": 6.311283613773434,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 32,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009484859073972673,
        0.04488204172407073,
        -0.04891987698566452
      ],
      "can_pose": [
        -0.34080755710601807,
        -0.1626347303390503,
        0.8328927159309387,
        -0.029141858220100403,
        0.10988014191389084,
        -0.08118360489606857,
        0.9901951551437378
      ],
      "can_relative_orientation_from_partial_start_rad": 1.3547419939471252,
      "can_relative_translation_from_partial_start_m": [
        -0.009259715676307678,
        -0.1102224588394165,
        -0.04925096035003662
      ],
      "can_to_box_relative_orientation_rad": 2.1062109583933775,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8097686767578125,
        -6.809776306152344
      ],
      "left_finger_qvel_mps": [
        -0.00011516078666318208,
        3.4676479117479175e-05
      ],
      "linear_speed_mps": 0.16910463215842111,
      "local_corner_max_m": [
        0.045578960195046286,
        0.09130262272169287,
        -0.00803682951700968
      ],
      "local_corner_min_m": [
        -0.0645486783429916,
        -0.0015385392735514092,
        -0.08980292445431937
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.029311100311164684,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.07019414777981953,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011571947157490159,
      "step_index": 2243,
      "timestamp_seconds": 8.972000426147133,
      "trace_row": 2243,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02330393458705277,
      "vertical_lower_margin_m": -0.02330393458705277,
      "vertical_upper_margin_m": 0.013462772591808489
    },
    {
      "actual_left_finger_qpos_m": [
        0.02280031330883503,
        0.022455116733908653
      ],
      "angular_speed_rps": 6.325172784941205,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 33,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009435924024697423,
        0.044810745680863406,
        -0.04953268921761006
      ],
      "can_pose": [
        -0.3414752185344696,
        -0.162567138671875,
        0.8326982259750366,
        -0.028543340042233467,
        0.09736233204603195,
        -0.08018679171800613,
        0.991602897644043
      ],
      "can_relative_orientation_from_partial_start_rad": 1.3791349882031403,
      "can_relative_translation_from_partial_start_m": [
        -0.009192124009132385,
        -0.1104169487953186,
        -0.04991862177848816
      ],
      "can_to_box_relative_orientation_rad": 2.117143654309582,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809720516204834,
        -6.8097243309021
      ],
      "left_finger_qvel_mps": [
        -0.0001694739912636578,
        6.0546561144292355e-05
      ],
      "linear_speed_mps": 0.17467232055461274,
      "local_corner_max_m": [
        0.045508900543987374,
        0.09049311236605873,
        -0.009229612048178293
      ],
      "local_corner_min_m": [
        -0.06438074859338222,
        -0.0008716210043319128,
        -0.08983576638704183
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.028698288079219147,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.06900136524865091,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01160478909021262,
      "step_index": 2244,
      "timestamp_seconds": 8.976000426337123,
      "trace_row": 2244,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.022637016317833273,
      "vertical_lower_margin_m": -0.022637016317833273,
      "vertical_upper_margin_m": 0.014272282947442635
    },
    {
      "actual_left_finger_qpos_m": [
        0.022799275815486908,
        0.022455353289842606
      ],
      "angular_speed_rps": 6.3676364871879985,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 34,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009353214771565671,
        0.04470427767182372,
        -0.050148022281845284
      ],
      "can_pose": [
        -0.3421454429626465,
        -0.16245709359645844,
        0.8324135541915894,
        -0.02792241796851158,
        0.08480748534202576,
        -0.07860743254423141,
        0.9928994178771973
      ],
      "can_relative_orientation_from_partial_start_rad": 1.4034150733460389,
      "can_relative_translation_from_partial_start_m": [
        -0.00908207893371582,
        -0.11070162057876587,
        -0.05058884620666504
      ],
      "can_to_box_relative_orientation_rad": 2.127520312764173,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8096537590026855,
        -6.809661388397217
      ],
      "left_finger_qvel_mps": [
        -0.00020088475139345974,
        2.9344191716518253e-05
      ],
      "linear_speed_mps": 0.18411081505426785,
      "local_corner_max_m": [
        0.04543850951581724,
        0.08957423726295966,
        -0.010451249882976466
      ],
      "local_corner_min_m": [
        -0.06414493905894858,
        -0.00016568191931221055,
        -0.0898447946807141
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.028082955014983924,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.06777972741385274,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011613817383884895,
      "step_index": 2245,
      "timestamp_seconds": 8.980000426527113,
      "trace_row": 2245,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02193107723281357,
      "vertical_lower_margin_m": -0.02193107723281357,
      "vertical_upper_margin_m": 0.015191158050541706
    },
    {
      "actual_left_finger_qpos_m": [
        0.02279829978942871,
        0.022455593571066856
      ],
      "angular_speed_rps": 6.397156131379526,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 33,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0092564369785689,
        0.044490991088001364,
        -0.050764710020852144
      ],
      "can_pose": [
        -0.3428163528442383,
        -0.1623300313949585,
        0.8319991230964661,
        -0.027318863198161125,
        0.072210893034935,
        -0.076785147190094,
        0.9940540194511414
      ],
      "can_relative_orientation_from_partial_start_rad": 1.4277157473697217,
      "can_relative_translation_from_partial_start_m": [
        -0.008955016732215881,
        -0.11111605167388916,
        -0.051259756088256836
      ],
      "can_to_box_relative_orientation_rad": 2.137819228346177,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809595584869385,
        -6.809598922729492
      ],
      "left_finger_qvel_mps": [
        -0.0002405824779998511,
        4.699732016888447e-05
      ],
      "linear_speed_mps": 0.19969006363990774,
      "local_corner_max_m": [
        0.045369376037339704,
        0.08850195033227293,
        -0.011700886735456328
      ],
      "local_corner_min_m": [
        -0.0638822499944775,
        0.0004800318437298001,
        -0.08982853330624796
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.027466267275977063,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.06653009056137288,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011597556009418752,
      "step_index": 2246,
      "timestamp_seconds": 8.984000426717103,
      "trace_row": 2246,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02128536346977156,
      "vertical_lower_margin_m": -0.02128536346977156,
      "vertical_upper_margin_m": 0.016263444981228434
    },
    {
      "actual_left_finger_qpos_m": [
        0.0227972324937582,
        0.022455841302871704
      ],
      "angular_speed_rps": 6.51531986461725,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 35,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.009117377450728714,
        0.04427712049663113,
        -0.05138605281666314
      ],
      "can_pose": [
        -0.34349218010902405,
        -0.16215050220489502,
        0.8315121531486511,
        -0.026713833212852478,
        0.05949676036834717,
        -0.07420283555984497,
        0.9951083660125732
      ],
      "can_relative_orientation_from_partial_start_rad": 1.4520389175866273,
      "can_relative_translation_from_partial_start_m": [
        -0.008775487542152405,
        -0.1116030216217041,
        -0.0519355833530426
      ],
      "can_to_box_relative_orientation_rad": 2.147470833081101,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809523582458496,
        -6.809534072875977
      ],
      "left_finger_qvel_mps": [
        -0.00020403657981660217,
        3.2760563044575974e-05
      ],
      "linear_speed_mps": 0.21303064377726874,
      "local_corner_max_m": [
        0.045300958657146895,
        0.08733451814521054,
        -0.012985830760619155
      ],
      "local_corner_min_m": [
        -0.06353571355860432,
        0.0012197228480517186,
        -0.08978627487270713
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.026844924480166066,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.06524514653621005,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01155529757587792,
      "step_index": 2247,
      "timestamp_seconds": 8.988000426907092,
      "trace_row": 2247,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02054567246544964,
      "vertical_lower_margin_m": -0.02054567246544964,
      "vertical_upper_margin_m": 0.017430877168290823
    },
    {
      "actual_left_finger_qpos_m": [
        0.022796308621764183,
        0.02245607227087021
      ],
      "angular_speed_rps": 6.560967157640967,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 36,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008933402500177212,
        0.044108517606901154,
        -0.05200374031306704
      ],
      "can_pose": [
        -0.3441649079322815,
        -0.16191363334655762,
        0.8309743404388428,
        -0.02614709548652172,
        0.04692815989255905,
        -0.07059849053621292,
        0.9960573315620422
      ],
      "can_relative_orientation_from_partial_start_rad": 1.475815634429113,
      "can_relative_translation_from_partial_start_m": [
        -0.008538618683815002,
        -0.11214083433151245,
        -0.05260831117630005
      ],
      "can_to_box_relative_orientation_rad": 2.1559351851317716,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809468746185303,
        -6.80947208404541
      ],
      "left_finger_qvel_mps": [
        -0.00023671230883337557,
        0.00010469942208146676
      ],
      "linear_speed_mps": 0.2233148023626891,
      "local_corner_max_m": [
        0.04522532097614432,
        0.08611016636674407,
        -0.014282618313977036
      ],
      "local_corner_min_m": [
        -0.06309212597649871,
        0.002106868847058241,
        -0.08972486231215704
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02622723698376217,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.06394835898285217,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011493885015327832,
      "step_index": 2248,
      "timestamp_seconds": 8.992000427097082,
      "trace_row": 2248,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.01965852646644312,
      "vertical_lower_margin_m": -0.01965852646644312,
      "vertical_upper_margin_m": 0.018655228946757293
    },
    {
      "actual_left_finger_qpos_m": [
        0.02279534563422203,
        0.022456303238868713
      ],
      "angular_speed_rps": 6.609179885535845,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 35,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008723534501261399,
        0.04388048908090614,
        -0.05262085335070571
      ],
      "can_pose": [
        -0.34483516216278076,
        -0.16164758801460266,
        0.8303319215774536,
        -0.02564172074198723,
        0.034391701221466064,
        -0.06651736050844193,
        0.9968627691268921
      ],
      "can_relative_orientation_from_partial_start_rad": 1.4994567366515896,
      "can_relative_translation_from_partial_start_m": [
        -0.008272573351860046,
        -0.11278325319290161,
        -0.053278565406799316
      ],
      "can_to_box_relative_orientation_rad": 2.164035939960704,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.80940055847168,
        -6.8094072341918945
      ],
      "left_finger_qvel_mps": [
        -0.00021620024926960468,
        4.098337740288116e-05
      ],
      "linear_speed_mps": 0.24144393202949618,
      "local_corner_max_m": [
        0.04515426967987565,
        0.08476272605723034,
        -0.015601759321371977
      ],
      "local_corner_min_m": [
        -0.06260133868239848,
        0.0029982521045819333,
        -0.08963994738003944
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.025610123946123498,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.06262921797545723,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011408970083210235,
      "step_index": 2249,
      "timestamp_seconds": 8.996000427287072,
      "trace_row": 2249,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.018767143208919427,
      "vertical_lower_margin_m": -0.018767143208919427,
      "vertical_upper_margin_m": 0.02000266925627102
    },
    {
      "actual_left_finger_qpos_m": [
        0.022794289514422417,
        0.022456537932157516
      ],
      "angular_speed_rps": 6.69547005968196,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 36,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008482362067443794,
        0.04361573835668875,
        -0.05323801398012418
      ],
      "can_pose": [
        -0.3455035090446472,
        -0.1613466888666153,
        0.8295961022377014,
        -0.02521049976348877,
        0.02186938002705574,
        -0.06184001639485359,
        0.997528076171875
      ],
      "can_relative_orientation_from_partial_start_rad": 1.522984667576235,
      "can_relative_translation_from_partial_start_m": [
        -0.00797167420387268,
        -0.11351907253265381,
        -0.05394691228866577
      ],
      "can_to_box_relative_orientation_rad": 2.1716716804317753,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809329509735107,
        -6.809336185455322
      ],
      "left_finger_qvel_mps": [
        -0.00023475386842619628,
        3.778074460569769e-05
      ],
      "linear_speed_mps": 0.2596461353995202,
      "local_corner_max_m": [
        0.045087671109141386,
        0.08330297912509133,
        -0.01694471286584559
      ],
      "local_corner_min_m": [
        -0.062052395244028946,
        0.003928497588286173,
        -0.08953131509440276
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02499296331670503,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.06128626443098362,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.011300337797573556,
      "step_index": 2250,
      "timestamp_seconds": 9.000000427477062,
      "trace_row": 2250,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.017836897725215187,
      "vertical_lower_margin_m": -0.017836897725215187,
      "vertical_upper_margin_m": 0.021462416188410036
    },
    {
      "actual_left_finger_qpos_m": [
        0.022793391719460487,
        0.022456767037510872
      ],
      "angular_speed_rps": 6.742159771248458,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 35,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.008230420732321858,
        0.043239356857809885,
        -0.053855154924778825
      ],
      "can_pose": [
        -0.3461689054965973,
        -0.16103704273700714,
        0.8287257552146912,
        -0.02486714906990528,
        0.009326726198196411,
        -0.0569266602396965,
        0.998025119304657
      ],
      "can_relative_orientation_from_partial_start_rad": 1.546580396381926,
      "can_relative_translation_from_partial_start_m": [
        -0.007662028074264526,
        -0.11438941955566406,
        -0.054612308740615845
      ],
      "can_to_box_relative_orientation_rad": 2.179337618278296,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809261322021484,
        -6.809268474578857
      ],
      "left_finger_qvel_mps": [
        -1.2235963367857039e-05,
        2.0825227693421766e-05
      ],
      "linear_speed_mps": 0.2846200297310278,
      "local_corner_max_m": [
        0.045025428392445804,
        0.0816841383162229,
        -0.018313624618744584
      ],
      "local_corner_min_m": [
        -0.06148626985708955,
        0.004794575399396872,
        -0.08939668523081307
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.024375822372050382,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05991735267808462,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01116570793398386,
      "step_index": 2251,
      "timestamp_seconds": 9.004000427667052,
      "trace_row": 2251,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.016970819914104488,
      "vertical_lower_margin_m": -0.016970819914104488,
      "vertical_upper_margin_m": 0.023081256997278463
    },
    {
      "actual_left_finger_qpos_m": [
        0.022792546078562737,
        0.022457003593444824
      ],
      "angular_speed_rps": 6.915994288097455,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 34,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.007939564751768768,
        0.04286156363869098,
        -0.05447364797292453
      ],
      "can_pose": [
        -0.346833735704422,
        -0.1606857180595398,
        0.827778160572052,
        -0.024630850180983543,
        -0.00326616782695055,
        -0.05122058466076851,
        0.9983783960342407
      ],
      "can_relative_orientation_from_partial_start_rad": 1.5701831543860807,
      "can_relative_translation_from_partial_start_m": [
        -0.00731070339679718,
        -0.11533701419830322,
        -0.05527713894844055
      ],
      "can_to_box_relative_orientation_rad": 2.186434846600976,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809199810028076,
        -6.809201717376709
      ],
      "left_finger_qvel_mps": [
        -0.000263632187852636,
        0.00012502464232966304
      ],
      "linear_speed_mps": 0.3024239265894111,
      "local_corner_max_m": [
        0.04496660295022775,
        0.08055389467366059,
        -0.019450428715607537
      ],
      "local_corner_min_m": [
        -0.06084573245376529,
        0.005169232603721374,
        -0.08949686723024153
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.023757329323904675,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05878054858122167,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01126588993341232,
      "step_index": 2252,
      "timestamp_seconds": 9.008000427857041,
      "trace_row": 2252,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.016596162709779986,
      "vertical_lower_margin_m": -0.016596162709779986,
      "vertical_upper_margin_m": 0.024211500639840774
    },
    {
      "actual_left_finger_qpos_m": [
        0.022791681811213493,
        0.022457236424088478
      ],
      "angular_speed_rps": 7.026783783590541,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 34,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.007631410100224195,
        0.04240349471954685,
        -0.055093051079913136
      ],
      "can_pose": [
        -0.3474959135055542,
        -0.16032026708126068,
        0.82671058177948,
        -0.024509219452738762,
        -0.01591804064810276,
        -0.04510635510087013,
        0.9985547661781311
      ],
      "can_relative_orientation_from_partial_start_rad": 1.593927967491035,
      "can_relative_translation_from_partial_start_m": [
        -0.006945252418518066,
        -0.11640459299087524,
        -0.055939316749572754
      ],
      "can_to_box_relative_orientation_rad": 2.1934542227138425,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.80912971496582,
        -6.809136867523193
      ],
      "left_finger_qvel_mps": [
        -0.000148217732203193,
        3.5014323657378554e-05
      ],
      "linear_speed_mps": 0.3270854412056074,
      "local_corner_max_m": [
        0.04491100071557763,
        0.0803119181813512,
        -0.019208436139549256
      ],
      "local_corner_min_m": [
        -0.06017382091602602,
        0.004495071257742511,
        -0.09097766602027701
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02313792621691607,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05902254115727995,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.012746688723447808,
      "step_index": 2253,
      "timestamp_seconds": 9.012000428047031,
      "trace_row": 2253,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.01727032405575885,
      "vertical_lower_margin_m": -0.01727032405575885,
      "vertical_upper_margin_m": 0.024453477132150167
    },
    {
      "actual_left_finger_qpos_m": [
        0.022790594026446342,
        0.022457467392086983
      ],
      "angular_speed_rps": 7.234305925671792,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 36,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.007293165866370799,
        0.04191872147664155,
        -0.055715369982990426
      ],
      "can_pose": [
        -0.3481571674346924,
        -0.15992727875709534,
        0.8255490660667419,
        -0.024521850049495697,
        -0.028684265911579132,
        -0.03829750046133995,
        0.9985537528991699
      ],
      "can_relative_orientation_from_partial_start_rad": 1.6178855695884886,
      "can_relative_translation_from_partial_start_m": [
        -0.006552264094352722,
        -0.11756610870361328,
        -0.05660057067871094
      ],
      "can_to_box_relative_orientation_rad": 2.200159656226253,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809059143066406,
        -6.80906343460083
      ],
      "left_finger_qvel_mps": [
        -0.0003005788312293589,
        4.432365676620975e-05
      ],
      "linear_speed_mps": 0.34828285454325514,
      "local_corner_max_m": [
        0.04485669356910599,
        0.07995905287007155,
        -0.018986872925924436
      ],
      "local_corner_min_m": [
        -0.059443025301847585,
        0.003878390083211558,
        -0.09244386704005642
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02251560731383878,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05924410437090477,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.014212889743227208,
      "step_index": 2254,
      "timestamp_seconds": 9.016000428237021,
      "trace_row": 2254,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.017887005230289802,
      "vertical_lower_margin_m": -0.017887005230289802,
      "vertical_upper_margin_m": 0.024806342443429816
    },
    {
      "actual_left_finger_qpos_m": [
        0.022789521142840385,
        0.022457696497440338
      ],
      "angular_speed_rps": 7.373974893049469,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 35,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00694146091230563,
        0.04134831713586429,
        -0.05633902342525127
      ],
      "can_pose": [
        -0.3488149642944336,
        -0.15952788293361664,
        0.8242623209953308,
        -0.024676769971847534,
        -0.041546791791915894,
        -0.031087281182408333,
        0.9983479976654053
      ],
      "can_relative_orientation_from_partial_start_rad": 1.642107317835029,
      "can_relative_translation_from_partial_start_m": [
        -0.0061528682708740234,
        -0.11885285377502441,
        -0.05725836753845215
      ],
      "can_to_box_relative_orientation_rad": 2.2069005273596196,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.809000015258789,
        -6.809004783630371
      ],
      "left_finger_qvel_mps": [
        -0.0003138309402856976,
        4.949971116730012e-05
      ],
      "linear_speed_mps": 0.37482715998151345,
      "local_corner_max_m": [
        0.04480374842715118,
        0.07945953711432485,
        -0.01878762042970361
      ],
      "local_corner_min_m": [
        -0.05868667025176244,
        0.0032370971574037233,
        -0.09389042642079892
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02189195387157794,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.059443356867125596,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.015659449123969715,
      "step_index": 2255,
      "timestamp_seconds": 9.02000042842701,
      "trace_row": 2255,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.018528298156097637,
      "vertical_lower_margin_m": -0.018528298156097637,
      "vertical_upper_margin_m": 0.02530585819917651
    },
    {
      "actual_left_finger_qpos_m": [
        0.02278844453394413,
        0.022457947954535484
      ],
      "angular_speed_rps": 7.8506735729612185,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 38,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.006512909139805428,
        0.04095857174584905,
        -0.056965053567788415
      ],
      "can_pose": [
        -0.34947383403778076,
        -0.15905484557151794,
        0.8229852318763733,
        -0.02510560117661953,
        -0.05440601706504822,
        -0.02209661155939102,
        0.9979586601257324
      ],
      "can_relative_orientation_from_partial_start_rad": 1.6661904000650725,
      "can_relative_translation_from_partial_start_m": [
        -0.00567983090877533,
        -0.12012994289398193,
        -0.057917237281799316
      ],
      "can_to_box_relative_orientation_rad": 2.2121466367884803,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808929443359375,
        -6.808935642242432
      ],
      "left_finger_qvel_mps": [
        -0.00030051416251808405,
        6.106777436798438e-05
      ],
      "linear_speed_mps": 0.3782219987134004,
      "local_corner_max_m": [
        0.044745206680877975,
        0.07894028152458776,
        -0.018613048726545733
      ],
      "local_corner_min_m": [
        -0.057771024960488804,
        0.0029768619671103336,
        -0.0953170584090311
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.021265923729040792,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.059617928570283474,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01708608111220189,
      "step_index": 2256,
      "timestamp_seconds": 9.024000428617,
      "trace_row": 2256,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.018788533346391027,
      "vertical_lower_margin_m": -0.018788533346391027,
      "vertical_upper_margin_m": 0.025825113788913598
    },
    {
      "actual_left_finger_qpos_m": [
        0.022787481546401978,
        0.022458167746663094
      ],
      "angular_speed_rps": 7.151699148578555,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 39,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00612612475015567,
        0.040432025944428185,
        -0.05735248736140869
      ],
      "can_pose": [
        -0.3497014045715332,
        -0.158632293343544,
        0.8216517567634583,
        -0.023711465299129486,
        -0.06596603244543076,
        -0.013805534690618515,
        0.9974446296691895
      ],
      "can_relative_orientation_from_partial_start_rad": 1.6878784546963708,
      "can_relative_translation_from_partial_start_m": [
        -0.005257278680801392,
        -0.12146341800689697,
        -0.05814480781555176
      ],
      "can_to_box_relative_orientation_rad": 2.214818017872523,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8088531494140625,
        -6.808858871459961
      ],
      "left_finger_qvel_mps": [
        -0.00016405939823016524,
        3.172921424265951e-05
      ],
      "linear_speed_mps": 0.35430340274660344,
      "local_corner_max_m": [
        0.044567289142181915,
        0.07825729296736073,
        -0.01848458833241956
      ],
      "local_corner_min_m": [
        -0.05681953864249323,
        0.0026067589214956444,
        -0.09622038639039782
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02087848993542052,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05974638896440965,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01798940909356861,
      "step_index": 2257,
      "timestamp_seconds": 9.02800042880699,
      "trace_row": 2257,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019158636392005716,
      "vertical_lower_margin_m": -0.019158636392005716,
      "vertical_upper_margin_m": 0.026508102346140636
    },
    {
      "actual_left_finger_qpos_m": [
        0.022786572575569153,
        0.022458398714661598
      ],
      "angular_speed_rps": 6.819424138451345,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.005751992713520976,
        0.039849721672947425,
        -0.05759424827279963
      ],
      "can_pose": [
        -0.3496387302875519,
        -0.15823031961917877,
        0.8202738761901855,
        -0.02099703997373581,
        -0.07639484107494354,
        -0.005467451177537441,
        0.9968416690826416
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7074038332189314,
      "can_relative_translation_from_partial_start_m": [
        -0.004855304956436157,
        -0.12284129858016968,
        -0.058082133531570435
      ],
      "can_to_box_relative_orientation_rad": 2.2147948934858017,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8087897300720215,
        -6.808796405792236
      ],
      "left_finger_qvel_mps": [
        -8.116105163935572e-05,
        2.0489773305598646e-05
      ],
      "linear_speed_mps": 0.3591714092079879,
      "local_corner_max_m": [
        0.04428319024108274,
        0.0774414190123387,
        -0.01843546665639839
      ],
      "local_corner_min_m": [
        -0.05578717566812469,
        0.0022580243335561523,
        -0.09675302988920087
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020636729024029576,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.059795510640430816,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018522052592371663,
      "step_index": 2258,
      "timestamp_seconds": 9.03200042899698,
      "trace_row": 2258,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019507370979945208,
      "vertical_lower_margin_m": -0.019507370979945208,
      "vertical_upper_margin_m": 0.027323976301162664
    },
    {
      "actual_left_finger_qpos_m": [
        0.022785523906350136,
        0.022458640858530998
      ],
      "angular_speed_rps": 5.025064070375026,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.005423714306388716,
        0.03967800864256987,
        -0.057873724410096195
      ],
      "can_pose": [
        -0.3495796322822571,
        -0.15788689255714417,
        0.8195794224739075,
        -0.017858227714896202,
        -0.08409909904003143,
        0.00014506286242976785,
        0.9962974190711975
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7219569807927764,
      "can_relative_translation_from_partial_start_m": [
        -0.00451187789440155,
        -0.12353575229644775,
        -0.058023035526275635
      ],
      "can_to_box_relative_orientation_rad": 2.2142327006707734,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808716297149658,
        -6.808722019195557
      ],
      "left_finger_qvel_mps": [
        -0.0002170535153709352,
        2.9912858735769987e-05
      ],
      "linear_speed_mps": 0.19424543557563537,
      "local_corner_max_m": [
        0.044077948941799866,
        0.07746773267891682,
        -0.018626079910527615
      ],
      "local_corner_min_m": [
        -0.054925377554577326,
        0.001888284606222923,
        -0.09712136890966477
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020357252886733013,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05960489738630159,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018890391612835566,
      "step_index": 2259,
      "timestamp_seconds": 9.03600042918697,
      "trace_row": 2259,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019877110707278437,
      "vertical_lower_margin_m": -0.019877110707278437,
      "vertical_upper_margin_m": 0.027297662634584538
    },
    {
      "actual_left_finger_qpos_m": [
        0.022784551605582237,
        0.022458896040916443
      ],
      "angular_speed_rps": 3.5411148567503754,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 41,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.005234563881723442,
        0.039819560250349495,
        -0.05816077097098976
      ],
      "can_pose": [
        -0.34952637553215027,
        -0.1576874554157257,
        0.8195422887802124,
        -0.014456517063081264,
        -0.08993196487426758,
        0.0022319757845252752,
        0.9958406686782837
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7332435523119425,
      "can_relative_translation_from_partial_start_m": [
        -0.004312440752983093,
        -0.12357288599014282,
        -0.05796977877616882
      ],
      "can_to_box_relative_orientation_rad": 2.2151282644141586,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808651924133301,
        -6.808657169342041
      ],
      "left_finger_qvel_mps": [
        -0.00011564209125936031,
        2.7515907277120277e-05
      ],
      "linear_speed_mps": 0.05243469857694659,
      "local_corner_max_m": [
        0.04404011917574924,
        0.07809751542415788,
        -0.01893956343985037
      ],
      "local_corner_min_m": [
        -0.05450924693919612,
        0.0015416050765411082,
        -0.09738197850212915
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020070206325839446,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.059291413856978836,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019151001205299945,
      "step_index": 2260,
      "timestamp_seconds": 9.04000042937696,
      "trace_row": 2260,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020223790236960252,
      "vertical_lower_margin_m": -0.020223790236960252,
      "vertical_upper_margin_m": 0.02666787988934348
    },
    {
      "actual_left_finger_qpos_m": [
        0.022783659398555756,
        0.02245911955833435
      ],
      "angular_speed_rps": 3.266694939720334,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.005073509057654829,
        0.03990994743286014,
        -0.05843626486622411
      ],
      "can_pose": [
        -0.34945785999298096,
        -0.15751847624778748,
        0.8195298314094543,
        -0.01096420269459486,
        -0.0952686220407486,
        0.003574036294594407,
        0.9953848719596863
      ],
      "can_relative_orientation_from_partial_start_rad": 1.743655341488223,
      "can_relative_translation_from_partial_start_m": [
        -0.004143461585044861,
        -0.12358534336090088,
        -0.05790126323699951
      ],
      "can_to_box_relative_orientation_rad": 2.2161989503268757,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808585166931152,
        -6.808589935302734
      ],
      "left_finger_qvel_mps": [
        -3.8820689951535314e-05,
        2.1699346689274535e-05
      ],
      "linear_speed_mps": 0.04569157554858867,
      "local_corner_max_m": [
        0.04409523784949462,
        0.07856971378803879,
        -0.019278896054672257
      ],
      "local_corner_min_m": [
        -0.05424225596480431,
        0.0012501810776814892,
        -0.09759363367777596
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0197947124306051,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05895208124215695,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019362656380946752,
      "step_index": 2261,
      "timestamp_seconds": 9.04400042956695,
      "trace_row": 2261,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02051521423581987,
      "vertical_lower_margin_m": -0.02051521423581987,
      "vertical_upper_margin_m": 0.026195681525462575
    },
    {
      "actual_left_finger_qpos_m": [
        0.022782867774367332,
        0.02245934121310711
      ],
      "angular_speed_rps": 3.052703067324682,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004933425166132738,
        0.039938280119992564,
        -0.05872038197751689
      ],
      "can_pose": [
        -0.3494059443473816,
        -0.15737266838550568,
        0.8195214867591858,
        -0.007499499712139368,
        -0.1002281978726387,
        0.00425585824996233,
        0.9949272274971008
      ],
      "can_relative_orientation_from_partial_start_rad": 1.753418395382137,
      "can_relative_translation_from_partial_start_m": [
        -0.0039976537227630615,
        -0.12359368801116943,
        -0.057849347591400146
      ],
      "can_to_box_relative_orientation_rad": 2.2176187516579025,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808513164520264,
        -6.808518886566162
      ],
      "left_finger_qvel_mps": [
        -9.307377331424505e-05,
        3.7802281440235674e-05
      ],
      "linear_speed_mps": 0.03874983698922015,
      "local_corner_max_m": [
        0.044085200847326284,
        0.07889025923704229,
        -0.019644848076712962
      ],
      "local_corner_min_m": [
        -0.05395205117959173,
        0.0009863010029428354,
        -0.09779591587832082
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01951059531931232,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058586129220116245,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01956493858149161,
      "step_index": 2262,
      "timestamp_seconds": 9.04800042975694,
      "trace_row": 2262,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020779094310558525,
      "vertical_lower_margin_m": -0.020779094310558525,
      "vertical_upper_margin_m": 0.025875136076459068
    },
    {
      "actual_left_finger_qpos_m": [
        0.02278207801282406,
        0.022459568455815315
      ],
      "angular_speed_rps": 2.878735391527265,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 41,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004820077058435679,
        0.039910484320223816,
        -0.05899907704720686
      ],
      "can_pose": [
        -0.34934762120246887,
        -0.1572553813457489,
        0.8195263743400574,
        -0.003953881561756134,
        -0.10474253445863724,
        0.004250111524015665,
        0.9944825768470764
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7623912026845365,
      "can_relative_translation_from_partial_start_m": [
        -0.0038803666830062866,
        -0.12358880043029785,
        -0.05779102444648743
      ],
      "can_to_box_relative_orientation_rad": 2.2192037724731857,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8084492683410645,
        -6.808452606201172
      ],
      "left_finger_qvel_mps": [
        -0.00011232258839299902,
        3.710167948156595e-05
      ],
      "linear_speed_mps": 0.03276977050386649,
      "local_corner_max_m": [
        0.043995516242375104,
        0.07905900707145364,
        -0.02003458570152361
      ],
      "local_corner_min_m": [
        -0.053635670359246435,
        0.0007619615689939963,
        -0.09796356839289011
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019231900249622347,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.0581963915953056,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019732591096060903,
      "step_index": 2263,
      "timestamp_seconds": 9.05200042994693,
      "trace_row": 2263,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021003433744507364,
      "vertical_lower_margin_m": -0.021003433744507364,
      "vertical_upper_margin_m": 0.025706388242047726
    },
    {
      "actual_left_finger_qpos_m": [
        0.02278127893805504,
        0.022459786385297775
      ],
      "angular_speed_rps": 2.130565355089684,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 43,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004748884198423786,
        0.03985040916482363,
        -0.05913596802920945
      ],
      "can_pose": [
        -0.3492625653743744,
        -0.15718257427215576,
        0.8195350766181946,
        -0.0015668445266783237,
        -0.1082204058766365,
        0.0037692105397582054,
        0.9941186904907227
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7693819940175148,
      "can_relative_translation_from_partial_start_m": [
        -0.003807559609413147,
        -0.12358009815216064,
        -0.057705968618392944
      ],
      "can_to_box_relative_orientation_rad": 2.221364637769935,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808382034301758,
        -6.808388710021973
      ],
      "left_finger_qvel_mps": [
        -9.446637704968452e-05,
        3.928999285562895e-05
      ],
      "linear_speed_mps": 0.028074779946625134,
      "local_corner_max_m": [
        0.04389604786947382,
        0.07910415002327453,
        -0.020222029044793477
      ],
      "local_corner_min_m": [
        -0.05339381626632139,
        0.0005966683063727274,
        -0.09804990701362543
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019095009267619756,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05800894825203573,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01981892971679622,
      "step_index": 2264,
      "timestamp_seconds": 9.056000430136919,
      "trace_row": 2264,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021168727007128633,
      "vertical_lower_margin_m": -0.021168727007128633,
      "vertical_upper_margin_m": 0.025661245290226828
    },
    {
      "actual_left_finger_qpos_m": [
        0.02278045006096363,
        0.022460006177425385
      ],
      "angular_speed_rps": 1.2241345946534081,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 43,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004709789331189096,
        0.03976882703762874,
        -0.05909848206076784
      ],
      "can_pose": [
        -0.34916993975639343,
        -0.15714281797409058,
        0.8195510506629944,
        -0.0008830535225570202,
        -0.11035426706075668,
        0.002810107544064522,
        0.9938880205154419
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7737645918701261,
      "can_relative_translation_from_partial_start_m": [
        -0.0037678033113479614,
        -0.12356412410736084,
        -0.05761334300041199
      ],
      "can_to_box_relative_orientation_rad": 2.2243097365425157,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8083086013793945,
        -6.8083109855651855
      ],
      "left_finger_qvel_mps": [
        -6.517886504298076e-05,
        2.9137267119949684e-05
      ],
      "linear_speed_mps": 0.025513767680501617,
      "local_corner_max_m": [
        0.04382771804331814,
        0.07903006095241194,
        -0.02013441825832618
      ],
      "local_corner_min_m": [
        -0.053247296705696334,
        0.0005075931228455399,
        -0.0980625458632095
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019132495236061364,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058096559038503026,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019831568566380298,
      "step_index": 2265,
      "timestamp_seconds": 9.060000430326909,
      "trace_row": 2265,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02125780219065582,
      "vertical_lower_margin_m": -0.02125780219065582,
      "vertical_upper_margin_m": 0.02573533436108942
    },
    {
      "actual_left_finger_qpos_m": [
        0.022779500111937523,
        0.022460248321294785
      ],
      "angular_speed_rps": 1.22101488451494,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004689373210939873,
        0.03963236514443469,
        -0.05907774966557661
      ],
      "can_pose": [
        -0.3491157293319702,
        -0.15712189674377441,
        0.8195773363113403,
        -0.0003443673485890031,
        -0.1120498776435852,
        0.0011476990766823292,
        0.9937019348144531
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7773530449765242,
      "can_relative_translation_from_partial_start_m": [
        -0.0037468820810317993,
        -0.12353783845901489,
        -0.05755913257598877
      ],
      "can_to_box_relative_orientation_rad": 2.2276601685077306,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808241367340088,
        -6.80824613571167
      ],
      "left_finger_qvel_mps": [
        -0.0001769889786373824,
        3.1442101317225024e-05
      ],
      "linear_speed_mps": 0.015944048491270093,
      "local_corner_max_m": [
        0.043698142342683044,
        0.07881260967420833,
        -0.020063854306883455
      ],
      "local_corner_min_m": [
        -0.05307688876456279,
        0.0004521206146610446,
        -0.09809164502426976
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0191532276312526,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05816712298994575,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01986066772744055,
      "step_index": 2266,
      "timestamp_seconds": 9.064000430516899,
      "trace_row": 2266,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021313274698840316,
      "vertical_lower_margin_m": -0.021313274698840316,
      "vertical_upper_margin_m": 0.025952785639293027
    },
    {
      "actual_left_finger_qpos_m": [
        0.022778615355491638,
        0.02246050350368023
      ],
      "angular_speed_rps": 0.41438289016059787,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707295953775059,
        0.03959516367878946,
        -0.05906654712039938
      ],
      "can_pose": [
        -0.349089652299881,
        -0.15713977813720703,
        0.819595456123352,
        -0.0001234742085216567,
        -0.1126154288649559,
        0.0005871735629625618,
        0.9936385154724121
      ],
      "can_relative_orientation_from_partial_start_rad": 1.77855132754323,
      "can_relative_translation_from_partial_start_m": [
        -0.0037647634744644165,
        -0.12351971864700317,
        -0.057533055543899536
      ],
      "can_to_box_relative_orientation_rad": 2.2287393492105054,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808166027069092,
        -6.808169841766357
      ],
      "left_finger_qvel_mps": [
        -0.00013432871492113918,
        3.253627801313996e-05
      ],
      "linear_speed_mps": 0.009110719287101577,
      "local_corner_max_m": [
        0.043627219615147955,
        0.07874713421387547,
        -0.02003988049613703
      ],
      "local_corner_min_m": [
        -0.053041811522698046,
        0.0004431931437034464,
        -0.09809321374466173
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019164430176429825,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05819109680069218,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019862236447832526,
      "step_index": 2267,
      "timestamp_seconds": 9.068000430706888,
      "trace_row": 2267,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021322202169797914,
      "vertical_lower_margin_m": -0.021322202169797914,
      "vertical_upper_margin_m": 0.02601826109962589
    },
    {
      "actual_left_finger_qpos_m": [
        0.022777803242206573,
        0.022460727021098137
      ],
      "angular_speed_rps": 0.014958802579900402,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00470693823479415,
        0.03959471145411031,
        -0.05906511022091904
      ],
      "can_pose": [
        -0.3490884006023407,
        -0.15713942050933838,
        0.8195942640304565,
        -0.00012630285345949233,
        -0.11258680373430252,
        0.0005946923629380763,
        0.9936418533325195
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7784929518109676,
      "can_relative_translation_from_partial_start_m": [
        -0.003764405846595764,
        -0.12352091073989868,
        -0.05753180384635925
      ],
      "can_to_box_relative_orientation_rad": 2.2286986123512236,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.8080973625183105,
        -6.808105945587158
      ],
      "left_finger_qvel_mps": [
        -7.488382834708318e-05,
        2.86726099147927e-05
      ],
      "linear_speed_mps": 0.0004412857351202281,
      "local_corner_max_m": [
        0.04362828062080781,
        0.0787460261263968,
        -0.020039666037960646
      ],
      "local_corner_min_m": [
        -0.053042157090396114,
        0.0004433967818238127,
        -0.09809055440387743
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01916586707591017,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05819131125886856,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01985957710704822,
      "step_index": 2268,
      "timestamp_seconds": 9.072000430896878,
      "trace_row": 2268,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021321998531677547,
      "vertical_lower_margin_m": -0.021321998531677547,
      "vertical_upper_margin_m": 0.026019369187104555
    },
    {
      "actual_left_finger_qpos_m": [
        0.02277696132659912,
        0.022460948675870895
      ],
      "angular_speed_rps": 0.026739311447008432,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706938320482579,
        0.03959476048880639,
        -0.05906281204554503
      ],
      "can_pose": [
        -0.3490859270095825,
        -0.15713942050933838,
        0.8195943236351013,
        -0.0001244924496859312,
        -0.11253369599580765,
        0.0005948087782599032,
        0.9936478734016418
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7783862018463603,
      "can_relative_translation_from_partial_start_m": [
        -0.003764405846595764,
        -0.1235208511352539,
        -0.057529330253601074
      ],
      "can_to_box_relative_orientation_rad": 2.2286305975290457,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.808027744293213,
        -6.808036804199219
      ],
      "left_finger_qvel_mps": [
        -0.00015772483311593533,
        3.7531186535488814e-05
      ],
      "linear_speed_mps": 0.0006185776661732693,
      "local_corner_max_m": [
        0.043628183854094366,
        0.07874345642133063,
        -0.020040162231787173
      ],
      "local_corner_min_m": [
        -0.053042060495059495,
        0.00044606455628215524,
        -0.09808546185930289
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019168165251284175,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058190815065042034,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019854484562473684,
      "step_index": 2269,
      "timestamp_seconds": 9.076000431086868,
      "trace_row": 2269,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021319330757219205,
      "vertical_lower_margin_m": -0.021319330757219205,
      "vertical_upper_margin_m": 0.026021938892170735
    },
    {
      "actual_left_finger_qpos_m": [
        0.02277596853673458,
        0.022461166605353355
      ],
      "angular_speed_rps": 0.04036519314759526,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00470695322585965,
        0.03959470142644472,
        -0.059059095439078335
      ],
      "can_pose": [
        -0.34908220171928406,
        -0.15713943541049957,
        0.8195942640304565,
        -0.00012445413449313492,
        -0.11245347559452057,
        0.0005948537145741284,
        0.9936569333076477
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7782250160243414,
      "can_relative_translation_from_partial_start_m": [
        -0.003764420747756958,
        -0.12352091073989868,
        -0.05752560496330261
      ],
      "can_to_box_relative_orientation_rad": 2.228531017540329,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807961463928223,
        -6.807966709136963
      ],
      "left_finger_qvel_mps": [
        -0.0002450057945679873,
        3.580718839657493e-05
      ],
      "linear_speed_mps": 0.000931449181632464,
      "local_corner_max_m": [
        0.04362816796528807,
        0.07873945769223367,
        -0.020040407031037488
      ],
      "local_corner_min_m": [
        -0.05304207441700737,
        0.0004499451606557736,
        -0.09807778384711918
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019171881857750872,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05819057026579172,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019846806550289975,
      "step_index": 2270,
      "timestamp_seconds": 9.080000431276858,
      "trace_row": 2270,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021315450152845587,
      "vertical_lower_margin_m": -0.021315450152845587,
      "vertical_upper_margin_m": 0.02602593762126769
    },
    {
      "actual_left_finger_qpos_m": [
        0.02277507819235325,
        0.022461382672190666
      ],
      "angular_speed_rps": 0.05490456851859281,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706923424419113,
        0.0395946455055759,
        -0.059054030924483136
      ],
      "can_pose": [
        -0.34907713532447815,
        -0.15713940560817719,
        0.8195942044258118,
        -0.0001245092280441895,
        -0.11234436184167862,
        0.0005949338665232062,
        0.9936692714691162
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7780057711659851,
      "can_relative_translation_from_partial_start_m": [
        -0.0037643909454345703,
        -0.12352097034454346,
        -0.057520538568496704
      ],
      "can_to_box_relative_orientation_rad": 2.2283956739130533,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00011761474888771772,
        2.7314672479406e-05
      ],
      "linear_speed_mps": 0.0012667082039346962,
      "local_corner_max_m": [
        0.04362820394185507,
        0.07873404440015408,
        -0.02004072235161014
      ],
      "local_corner_min_m": [
        -0.053042050790693296,
        0.00045524661099771713,
        -0.09806733949735613
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01917694637234607,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058190254945219066,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019836362200526925,
      "step_index": 2271,
      "timestamp_seconds": 9.084000431466848,
      "trace_row": 2271,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021310148702503643,
      "vertical_lower_margin_m": -0.021310148702503643,
      "vertical_upper_margin_m": 0.02603135091334728
    },
    {
      "actual_left_finger_qpos_m": [
        0.02277429774403572,
        0.022461598739027977
      ],
      "angular_speed_rps": 0.06961791028903111,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706953226617239,
        0.03959451567355521,
        -0.05904768258693671
      ],
      "can_pose": [
        -0.34907078742980957,
        -0.15713943541049957,
        0.8195940852165222,
        -0.00012459055869840086,
        -0.11220600455999374,
        0.0005948723992332816,
        0.9936848878860474
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7777277923187575,
      "can_relative_translation_from_partial_start_m": [
        -0.003764420747756958,
        -0.12352108955383301,
        -0.057514190673828125
      ],
      "can_to_box_relative_orientation_rad": 2.228224265801632,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00014384205860551447,
        5.750839409301989e-05
      ],
      "linear_speed_mps": 0.0015872708875453371,
      "local_corner_max_m": [
        0.043628170874824346,
        0.07872710330229116,
        -0.02004119537404958
      ],
      "local_corner_min_m": [
        -0.05304207732805882,
        0.00046192804481925975,
        -0.09805416979982384
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019183294709892496,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058189781922779626,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019823192502994635,
      "step_index": 2272,
      "timestamp_seconds": 9.088000431656837,
      "trace_row": 2272,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.0213034672686821,
      "vertical_lower_margin_m": -0.0213034672686821,
      "vertical_upper_margin_m": 0.026038292011210204
    },
    {
      "actual_left_finger_qpos_m": [
        0.02277335338294506,
        0.02246185950934887
      ],
      "angular_speed_rps": 0.08433830408119485,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706938324858634,
        0.03959444431491976,
        -0.059039962354726305
      ],
      "can_pose": [
        -0.34906306862831116,
        -0.15713942050933838,
        0.8195940256118774,
        -0.00012469978537410498,
        -0.11203839629888535,
        0.0005948085454292595,
        0.9937038421630859
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7773910351664948,
      "can_relative_translation_from_partial_start_m": [
        -0.003764405846595764,
        -0.12352114915847778,
        -0.05750647187232971
      ],
      "can_to_box_relative_orientation_rad": 2.228016630195306,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00022475954028777778,
        6.265337287914008e-05
      ],
      "linear_speed_mps": 0.0019297614112572825,
      "local_corner_max_m": [
        0.04362818319838585,
        0.07871877753186785,
        -0.02004174198899672
      ],
      "local_corner_min_m": [
        -0.05304205984810312,
        0.0004701110979716816,
        -0.09803818272045589
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019191014942102902,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05818923530783249,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019807205423626684,
      "step_index": 2273,
      "timestamp_seconds": 9.092000431846827,
      "trace_row": 2273,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02129528421552968,
      "vertical_lower_margin_m": -0.02129528421552968,
      "vertical_upper_margin_m": 0.026046617781633516
    },
    {
      "actual_left_finger_qpos_m": [
        0.02277258038520813,
        0.02246207371354103
      ],
      "angular_speed_rps": 0.09936633727672603,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706953226796873,
        0.0395942995469073,
        -0.059030724816607594
      ],
      "can_pose": [
        -0.34905382990837097,
        -0.15713943541049957,
        0.8195939064025879,
        -0.0001247847976628691,
        -0.11184091120958328,
        0.0005946143064647913,
        0.9937260746955872
      ],
      "can_relative_orientation_from_partial_start_rad": 1.776994285698188,
      "can_relative_translation_from_partial_start_m": [
        -0.003764420747756958,
        -0.12352126836776733,
        -0.057497233152389526
      ],
      "can_to_box_relative_orientation_rad": 2.2277721026913553,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -8.194254769477993e-05,
        3.308363739051856e-05
      ],
      "linear_speed_mps": 0.0023098751443928456,
      "local_corner_max_m": [
        0.04362815418778082,
        0.07870888993431857,
        -0.020042252947424122
      ],
      "local_corner_min_m": [
        -0.05304206064137457,
        0.00047970915949602233,
        -0.09801919668579107
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019200252480221613,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058188724349405085,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01978821938896186,
      "step_index": 2274,
      "timestamp_seconds": 9.096000432036817,
      "trace_row": 2274,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021285686154005338,
      "vertical_lower_margin_m": -0.021285686154005338,
      "vertical_upper_margin_m": 0.02605650537918279
    },
    {
      "actual_left_finger_qpos_m": [
        0.022771818563342094,
        0.02246229723095894
      ],
      "angular_speed_rps": 0.11516620639735219,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706953225898314,
        0.03959409392225255,
        -0.05902026194502119
      ],
      "can_pose": [
        -0.3490433692932129,
        -0.15713943541049957,
        0.8195937275886536,
        -0.0001249246415682137,
        -0.11161202937364578,
        0.0005944143049418926,
        0.9937518835067749
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7765344485354617,
      "can_relative_translation_from_partial_start_m": [
        -0.003764420747756958,
        -0.12352144718170166,
        -0.057486772537231445
      ],
      "can_to_box_relative_orientation_rad": 2.2274887420655998,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -7.5851858127862215e-06,
        2.0185179891996086e-05
      ],
      "linear_speed_mps": 0.002615535718437774,
      "local_corner_max_m": [
        0.04362814201762916,
        0.07869738742858767,
        -0.02004309266418325
      ],
      "local_corner_min_m": [
        -0.053042048469425784,
        0.0004908004159174251,
        -0.09799743122585913
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019210715351808016,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05818788463264596,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019766453929029926,
      "step_index": 2275,
      "timestamp_seconds": 9.100000432226807,
      "trace_row": 2275,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021274594897583935,
      "vertical_lower_margin_m": -0.021274594897583935,
      "vertical_upper_margin_m": 0.026068007884913688
    },
    {
      "actual_left_finger_qpos_m": [
        0.022770989686250687,
        0.0224625151604414
      ],
      "angular_speed_rps": 0.1303690047720722,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706968123243199,
        0.039594005181938896,
        -0.05900836255939684
      ],
      "can_pose": [
        -0.3490314781665802,
        -0.15713945031166077,
        0.8195936679840088,
        -0.00012514408444985747,
        -0.11135290563106537,
        0.0005941937561146915,
        0.9937808513641357
      ],
      "can_relative_orientation_from_partial_start_rad": 1.776013910082182,
      "can_relative_translation_from_partial_start_m": [
        -0.003764435648918152,
        -0.12352150678634644,
        -0.057474881410598755
      ],
      "can_to_box_relative_orientation_rad": 2.227168076411662,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00013381559983827174,
        3.469156945357099e-05
      ],
      "linear_speed_mps": 0.002972821197116803,
      "local_corner_max_m": [
        0.043628117290648555,
        0.07868450175268893,
        -0.02004399207411678
      ],
      "local_corner_min_m": [
        -0.05304205353713498,
        0.0005035086111888631,
        -0.09797273304467691
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019222614737432364,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05818698522271243,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.0197417557478477,
      "step_index": 2276,
      "timestamp_seconds": 9.104000432416797,
      "trace_row": 2276,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021261886702312497,
      "vertical_lower_margin_m": -0.021261886702312497,
      "vertical_upper_margin_m": 0.026080893560812432
    },
    {
      "actual_left_finger_qpos_m": [
        0.022770138457417488,
        0.0224627498537302
      ],
      "angular_speed_rps": 0.14620587886117822,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004706983023716527,
        0.03959391127201217,
        -0.058994949667028285
      ],
      "can_pose": [
        -0.34901806712150574,
        -0.15713946521282196,
        0.819593608379364,
        -0.0001253110240213573,
        -0.11106231063604355,
        0.0005939381080679595,
        0.9938133955001831
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7754301382177107,
      "can_relative_translation_from_partial_start_m": [
        -0.0037644505500793457,
        -0.12352156639099121,
        -0.05746147036552429
      ],
      "can_to_box_relative_orientation_rad": 2.2268084276380273,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -3.7941645132377744e-05,
        1.8992068362422287e-05
      ],
      "linear_speed_mps": 0.0033527962924791055,
      "local_corner_max_m": [
        0.0436280862307111,
        0.07867004207144157,
        -0.02004495286827912
      ],
      "local_corner_min_m": [
        -0.053042052278144125,
        0.0005177804725827739,
        -0.09794494646577745
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019236027629800923,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05818602442855009,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019713969168948242,
      "step_index": 2277,
      "timestamp_seconds": 9.108000432606786,
      "trace_row": 2277,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021247614840918586,
      "vertical_lower_margin_m": -0.021247614840918586,
      "vertical_upper_margin_m": 0.02609535324205979
    },
    {
      "actual_left_finger_qpos_m": [
        0.022769315168261528,
        0.022462991997599602
      ],
      "angular_speed_rps": 0.16263147506185516,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707012828046808,
        0.03959361869939715,
        -0.05898002225497723
      ],
      "can_pose": [
        -0.3490031361579895,
        -0.15713949501514435,
        0.8195933699607849,
        -0.00012541977048385888,
        -0.11073905974626541,
        0.0005934931105002761,
        0.993849515914917
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7747808006777688,
      "can_relative_translation_from_partial_start_m": [
        -0.0037644803524017334,
        -0.12352180480957031,
        -0.05744653940200806
      ],
      "can_to_box_relative_orientation_rad": 2.226408528691548,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00016884051728993654,
        4.52247986686416e-05
      ],
      "linear_speed_mps": 0.0037332239915502867,
      "local_corner_max_m": [
        0.043628022484209494,
        0.07865373788365504,
        -0.020046035290476938
      ],
      "local_corner_min_m": [
        -0.05304204814030311,
        0.0005334995151392574,
        -0.09791400921947752
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01925095504185198,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05818494200635227,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01968303192264831,
      "step_index": 2278,
      "timestamp_seconds": 9.112000432796776,
      "trace_row": 2278,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021231895798362103,
      "vertical_lower_margin_m": -0.021231895798362103,
      "vertical_upper_margin_m": 0.02611165742984632
    },
    {
      "actual_left_finger_qpos_m": [
        0.022768400609493256,
        0.022463206201791763
      ],
      "angular_speed_rps": 0.1795276616526915,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00470701282346242,
        0.0395933836732012,
        -0.05896347207019992
      ],
      "can_pose": [
        -0.34898659586906433,
        -0.15713949501514435,
        0.8195931911468506,
        -0.0001256886898772791,
        -0.11038219928741455,
        0.0005930229090154171,
        0.9938891530036926
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7740640023910261,
      "can_relative_translation_from_partial_start_m": [
        -0.0037644803524017334,
        -0.12352198362350464,
        -0.057429999113082886
      ],
      "can_to_box_relative_orientation_rad": 2.2259673010324614,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -2.4177730665542185e-05,
        1.2450938811525702e-05
      ],
      "linear_speed_mps": 0.004135313668267721,
      "local_corner_max_m": [
        0.04362799511181703,
        0.07863581217795379,
        -0.020047163331846307
      ],
      "local_corner_min_m": [
        -0.05304202075874187,
        0.000550955168448608,
        -0.09787978080855353
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01926750522662929,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.0581838139649829,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019648803511724322,
      "step_index": 2279,
      "timestamp_seconds": 9.116000432986766,
      "trace_row": 2279,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021214440145052752,
      "vertical_lower_margin_m": -0.021214440145052752,
      "vertical_upper_margin_m": 0.02612958313554757
    },
    {
      "actual_left_finger_qpos_m": [
        0.0227675661444664,
        0.022463424131274223
      ],
      "angular_speed_rps": 0.197325156155463,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707027721979062,
        0.03959321220380729,
        -0.058945316707242956
      ],
      "can_pose": [
        -0.3489684462547302,
        -0.15713950991630554,
        0.819593071937561,
        -0.00012594218424055725,
        -0.1099899485707283,
        0.0005926114972680807,
        0.9939326047897339
      ],
      "can_relative_orientation_from_partial_start_rad": 1.773276131826489,
      "can_relative_translation_from_partial_start_m": [
        -0.0037644952535629272,
        -0.12352210283279419,
        -0.05741184949874878
      ],
      "can_to_box_relative_orientation_rad": 2.2254822588332974,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00013860594481229782,
        3.507133078528568e-05
      ],
      "linear_speed_mps": 0.00453750276916324,
      "local_corner_max_m": [
        0.043627955313683325,
        0.07861618268847181,
        -0.020048467078911447
      ],
      "local_corner_min_m": [
        -0.05304201075764148,
        0.0005702417191427722,
        -0.09784216633557447
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01928566058958625,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05818251021791776,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019611189038745258,
      "step_index": 2280,
      "timestamp_seconds": 9.120000433176756,
      "trace_row": 2280,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021195153594358588,
      "vertical_lower_margin_m": -0.021195153594358588,
      "vertical_upper_margin_m": 0.026149212625029547
    },
    {
      "actual_left_finger_qpos_m": [
        0.022766828536987305,
        0.022463636472821236
      ],
      "angular_speed_rps": 0.21541494013033347,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707042622097812,
        0.03959277565372277,
        -0.05892561498285953
      ],
      "can_pose": [
        -0.34894874691963196,
        -0.15713952481746674,
        0.8195927143096924,
        -0.0001261536090169102,
        -0.1095617264509201,
        0.0005919382674619555,
        0.9939799308776855
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7724160600980974,
      "can_relative_translation_from_partial_start_m": [
        -0.003764510154724121,
        -0.12352246046066284,
        -0.05739215016365051
      ],
      "can_to_box_relative_orientation_rad": 2.2249530367164096,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -3.240596197429113e-05,
        3.1907009542919695e-05
      ],
      "linear_speed_mps": 0.004925646443454078,
      "local_corner_max_m": [
        0.0436278933870812,
        0.07859445438333879,
        -0.020050039961911792
      ],
      "local_corner_min_m": [
        -0.0530419786312768,
        0.0005910969241067487,
        -0.09780119000380727
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019305362313969676,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058180937334917415,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019570212706978063,
      "step_index": 2281,
      "timestamp_seconds": 9.124000433366746,
      "trace_row": 2281,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02117429838939461,
      "vertical_lower_margin_m": -0.02117429838939461,
      "vertical_upper_margin_m": 0.026170940930162576
    },
    {
      "actual_left_finger_qpos_m": [
        0.022765997797250748,
        0.022463852539658546
      ],
      "angular_speed_rps": 0.23373128909037919,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707102218853676,
        0.03959253371678073,
        -0.058904200701314524
      ],
      "can_pose": [
        -0.3489273488521576,
        -0.1571395844221115,
        0.8195925354957581,
        -0.00012655192404054105,
        -0.10909706354141235,
        0.0005914271459914744,
        0.9940310120582581
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7714828356392782,
      "can_relative_translation_from_partial_start_m": [
        -0.0037645697593688965,
        -0.12352263927459717,
        -0.05737075209617615
      ],
      "can_to_box_relative_orientation_rad": 2.2243788883630584,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00012035012332489714,
        3.166112583130598e-05
      ],
      "linear_speed_mps": 0.005349724147531434,
      "local_corner_max_m": [
        0.043627808297106774,
        0.07857110035025472,
        -0.020051728036658445
      ],
      "local_corner_min_m": [
        -0.053042012734814126,
        0.0006139670833067434,
        -0.0977566733659706
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019326776595514683,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05817924926017076,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019525696069141396,
      "step_index": 2282,
      "timestamp_seconds": 9.128000433556736,
      "trace_row": 2282,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021151428230194617,
      "vertical_lower_margin_m": -0.021151428230194617,
      "vertical_upper_margin_m": 0.026194294963246642
    },
    {
      "actual_left_finger_qpos_m": [
        0.02276526764035225,
        0.02246403880417347
      ],
      "angular_speed_rps": 0.2527427279220728,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707117115821391,
        0.03959208313048879,
        -0.05888103599274436
      ],
      "can_pose": [
        -0.34890419244766235,
        -0.1571395993232727,
        0.8195921778678894,
        -0.00012685869296547025,
        -0.10859458148479462,
        0.0005906268488615751,
        0.9940860271453857
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7704737329212281,
      "can_relative_translation_from_partial_start_m": [
        -0.0037645846605300903,
        -0.12352299690246582,
        -0.05734759569168091
      ],
      "can_to_box_relative_orientation_rad": 2.2237583286474814,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -4.9062400648836046e-05,
        2.3583190341014415e-05
      ],
      "linear_speed_mps": 0.005789792407407266,
      "local_corner_max_m": [
        0.04362774095425928,
        0.07854559438264286,
        -0.020053592355192495
      ],
      "local_corner_min_m": [
        -0.053041975185902035,
        0.000638571878334715,
        -0.09770847963029622
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01934994130408485,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05817738494163671,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01947750233346701,
      "step_index": 2283,
      "timestamp_seconds": 9.132000433746725,
      "trace_row": 2283,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021126823435166645,
      "vertical_lower_margin_m": -0.021126823435166645,
      "vertical_upper_margin_m": 0.026219800930858503
    },
    {
      "actual_left_finger_qpos_m": [
        0.022764382883906364,
        0.02246425487101078
      ],
      "angular_speed_rps": 0.27264139413453997,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00470713200734979,
        0.03959164240151347,
        -0.05885601266342477
      ],
      "can_pose": [
        -0.3488791882991791,
        -0.1571396142244339,
        0.8195918202400208,
        -0.00012731703463941813,
        -0.10805251449346542,
        0.0005899312673136592,
        0.9941451549530029
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7693851662250464,
      "can_relative_translation_from_partial_start_m": [
        -0.003764599561691284,
        -0.12352335453033447,
        -0.05732259154319763
      ],
      "can_to_box_relative_orientation_rad": 2.2230890430212313,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00016372330719605088,
        4.092958988621831e-05
      ],
      "linear_speed_mps": 0.006251677283473047,
      "local_corner_max_m": [
        0.043627688934945286,
        0.07851809840896629,
        -0.02005560270443507
      ],
      "local_corner_min_m": [
        -0.053041952949644866,
        0.0006651863940606573,
        -0.09765642262241447
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019374964633404435,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058175374592394136,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019425445325585267,
      "step_index": 2284,
      "timestamp_seconds": 9.136000433936715,
      "trace_row": 2284,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021100208919440703,
      "vertical_lower_margin_m": -0.021100208919440703,
      "vertical_upper_margin_m": 0.026247296904535075
    },
    {
      "actual_left_finger_qpos_m": [
        0.022763654589653015,
        0.022464465349912643
      ],
      "angular_speed_rps": 0.2932565731894618,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707161802199933,
        0.03959105413671371,
        -0.05882899769242844
      ],
      "can_pose": [
        -0.3488521873950958,
        -0.1571396440267563,
        0.8195913434028625,
        -0.00012771754700224847,
        -0.10746940225362778,
        0.0005889599560759962,
        0.9942082166671753
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7682143172706295,
      "can_relative_translation_from_partial_start_m": [
        -0.003764629364013672,
        -0.12352383136749268,
        -0.05729559063911438
      ],
      "can_to_box_relative_orientation_rad": 2.2223695011775084,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -7.276248652487993e-06,
        2.2309286578092724e-05
      ],
      "linear_speed_mps": 0.006751282349900436,
      "local_corner_max_m": [
        0.043627597937320184,
        0.07848833515903786,
        -0.02005772363700603
      ],
      "local_corner_min_m": [
        -0.05304192154172005,
        0.000693773114389562,
        -0.09760027174785085
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019401979604400765,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058173253659823176,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019369294451021646,
      "step_index": 2285,
      "timestamp_seconds": 9.140000434126705,
      "trace_row": 2285,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021071622199111798,
      "vertical_lower_margin_m": -0.021071622199111798,
      "vertical_upper_margin_m": 0.026277060154463502
    },
    {
      "actual_left_finger_qpos_m": [
        0.02276279404759407,
        0.022464679554104805
      ],
      "angular_speed_rps": 0.29497678250001813,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0047100671073985745,
        0.03959441459476254,
        -0.05880213951669683
      ],
      "can_pose": [
        -0.3488253355026245,
        -0.1571425497531891,
        0.8196007013320923,
        -0.00012142505147494376,
        -0.10688619315624237,
        0.0005264814244583249,
        0.9942712187767029
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7670504238914149,
      "can_relative_translation_from_partial_start_m": [
        -0.003767535090446472,
        -0.12351447343826294,
        -0.057268738746643066
      ],
      "can_to_box_relative_orientation_rad": 2.2217111981306497,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00021872020442970097,
        4.582455585477874e-05
      ],
      "linear_speed_mps": 0.0071459697437067145,
      "local_corner_max_m": [
        0.043619831878210336,
        0.07845649346144845,
        -0.02006006726295123
      ],
      "local_corner_min_m": [
        -0.053039966093007485,
        0.0007323357280766274,
        -0.09754421177044242
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01942883778013238,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058170910033877976,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019313234473613217,
      "step_index": 2286,
      "timestamp_seconds": 9.144000434316695,
      "trace_row": 2286,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021033059585424733,
      "vertical_lower_margin_m": -0.021033059585424733,
      "vertical_upper_margin_m": 0.02630890185205291
    },
    {
      "actual_left_finger_qpos_m": [
        0.022762024775147438,
        0.022464880719780922
      ],
      "angular_speed_rps": 0.31658005420977514,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0047072511760847535,
        0.03958990904218307,
        -0.05877320301632727
      ],
      "can_pose": [
        -0.34879645705223083,
        -0.15713973343372345,
        0.8195903897285461,
        -0.00012896455882582814,
        -0.10625959187746048,
        0.0005873207119293511,
        0.99433833360672
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7657852243699796,
      "can_relative_translation_from_partial_start_m": [
        -0.003764718770980835,
        -0.12352478504180908,
        -0.05723986029624939
      ],
      "can_to_box_relative_orientation_rad": 2.220877451145651,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -5.900904579902999e-05,
        3.3479544072179124e-05
      ],
      "linear_speed_mps": 0.007698318120248706,
      "local_corner_max_m": [
        0.04362743281910919,
        0.07842653282850665,
        -0.020062509068591028
      ],
      "local_corner_min_m": [
        -0.0530419351712787,
        0.0007532852558594927,
        -0.09748389696406351
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019457774280501938,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05816846822823818,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019252919667234303,
      "step_index": 2287,
      "timestamp_seconds": 9.148000434506685,
      "trace_row": 2287,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.021012110057641867,
      "vertical_lower_margin_m": -0.021012110057641867,
      "vertical_upper_margin_m": 0.026338862484994716
    },
    {
      "actual_left_finger_qpos_m": [
        0.022761326283216476,
        0.022465091198682785
      ],
      "angular_speed_rps": 0.3384884357598741,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707280965735916,
        0.0395892885677962,
        -0.05874212668484169
      ],
      "can_pose": [
        -0.34876540303230286,
        -0.15713976323604584,
        0.8195899128913879,
        -0.00012947831419296563,
        -0.10558642446994781,
        0.0005860355449840426,
        0.9944100379943848
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7644338120455076,
      "can_relative_translation_from_partial_start_m": [
        -0.0037647485733032227,
        -0.12352526187896729,
        -0.05720880627632141
      ],
      "can_to_box_relative_orientation_rad": 2.220047941489241,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -4.9731032049749047e-05,
        3.52481692971196e-05
      ],
      "linear_speed_mps": 0.007764423368443619,
      "local_corner_max_m": [
        0.04362732390132784,
        0.07839202765172748,
        -0.020065250175242022
      ],
      "local_corner_min_m": [
        -0.05304188583279967,
        0.0007865494838649179,
        -0.09741900319444136
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019488850611987518,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058165727121587185,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01918802589761215,
      "step_index": 2288,
      "timestamp_seconds": 9.152000434696674,
      "trace_row": 2288,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020978845829636442,
      "vertical_lower_margin_m": -0.020978845829636442,
      "vertical_upper_margin_m": 0.02637336766177388
    },
    {
      "actual_left_finger_qpos_m": [
        0.022760596126317978,
        0.02246529795229435
      ],
      "angular_speed_rps": 0.3617772564745959,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707355453758916,
        0.039588378572075866,
        -0.058708984180112056
      ],
      "can_pose": [
        -0.3487322926521301,
        -0.1571398377418518,
        0.8195891380310059,
        -0.00013013643911108375,
        -0.1048668920993805,
        0.0005848448490723968,
        0.9944862127304077
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7629894020027874,
      "can_relative_translation_from_partial_start_m": [
        -0.003764823079109192,
        -0.12352603673934937,
        -0.05717569589614868
      ],
      "can_to_box_relative_orientation_rad": 2.2191615909750895,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -8.694417920196429e-05,
        3.4527023672126234e-05
      ],
      "linear_speed_mps": 0.008279881984021988,
      "local_corner_max_m": [
        0.04362718438811056,
        0.0783548415912868,
        -0.020068321774151743
      ],
      "local_corner_min_m": [
        -0.053041895295628416,
        0.0008219155528649269,
        -0.09734964658607237
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01952199311671715,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058162655522677464,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019118669289243162,
      "step_index": 2289,
      "timestamp_seconds": 9.156000434886664,
      "trace_row": 2289,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020943479760636433,
      "vertical_lower_margin_m": -0.020943479760636433,
      "vertical_upper_margin_m": 0.026410553722214555
    },
    {
      "actual_left_finger_qpos_m": [
        0.022759782150387764,
        0.022465495392680168
      ],
      "angular_speed_rps": 0.38505386059480473,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004707400131032102,
        0.03958747193357648,
        -0.058673649636699965
      ],
      "can_pose": [
        -0.3486970067024231,
        -0.1571398824453354,
        0.8195883631706238,
        -0.00013100287469569594,
        -0.10410099476575851,
        0.000583687680773437,
        0.9945666193962097
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7614520521496824,
      "can_relative_translation_from_partial_start_m": [
        -0.0037648677825927734,
        -0.12352681159973145,
        -0.05714040994644165
      ],
      "can_to_box_relative_orientation_rad": 2.2182186324034303,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -8.511458145221695e-05,
        3.1575509638059884e-05
      ],
      "linear_speed_mps": 0.00882362076830246,
      "local_corner_max_m": [
        0.04362708815790592,
        0.07831524793259292,
        -0.02007160555157822
      ],
      "local_corner_min_m": [
        -0.05304188841997015,
        0.0008596959345600341,
        -0.09727569372182171
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019557327660129242,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05815937174525099,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.019044716424992503,
      "step_index": 2290,
      "timestamp_seconds": 9.160000435076654,
      "trace_row": 2290,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020905699378941326,
      "vertical_lower_margin_m": -0.020905699378941326,
      "vertical_upper_margin_m": 0.026450147380908437
    },
    {
      "actual_left_finger_qpos_m": [
        0.022758962586522102,
        0.022465702146291733
      ],
      "angular_speed_rps": 0.403789323447762,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00470745971138023,
        0.03958649366470324,
        -0.058636591832891216
      ],
      "can_pose": [
        -0.3486599922180176,
        -0.15713994204998016,
        0.8195875287055969,
        -0.00013182780821807683,
        -0.10329777747392654,
        0.0005824241088703275,
        0.9946504235267639
      ],
      "can_relative_orientation_from_partial_start_rad": 1.759839908397265,
      "can_relative_translation_from_partial_start_m": [
        -0.003764927387237549,
        -0.1235276460647583,
        -0.05710339546203613
      ],
      "can_to_box_relative_orientation_rad": 2.217230151162616,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00016499274352099746,
        3.1924821087159216e-05
      ],
      "linear_speed_mps": 0.00925598390969556,
      "local_corner_max_m": [
        0.0436269662584472,
        0.07827359588103633,
        -0.020075151170335537
      ],
      "local_corner_min_m": [
        -0.05304188568120766,
        0.000899391448370146,
        -0.0971980324954469
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01959438546393799,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05815582612649367,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01896705519861769,
      "step_index": 2291,
      "timestamp_seconds": 9.164000435266644,
      "trace_row": 2291,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020866003865131214,
      "vertical_lower_margin_m": -0.020866003865131214,
      "vertical_upper_margin_m": 0.026491799432465032
    },
    {
      "actual_left_finger_qpos_m": [
        0.022758180275559425,
        0.022465908899903297
      ],
      "angular_speed_rps": 0.4125173573193761,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004708100387239483,
        0.03958620835178006,
        -0.05859875936876202
      ],
      "can_pose": [
        -0.34862220287323,
        -0.1571405827999115,
        0.8195886611938477,
        -0.00013129210856277496,
        -0.10247723758220673,
        0.0005678459419868886,
        0.9947351813316345
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7581947234642166,
      "can_relative_translation_from_partial_start_m": [
        -0.0037655681371688843,
        -0.12352651357650757,
        -0.057065606117248535
      ],
      "can_to_box_relative_orientation_rad": 2.2162341795903684,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -6.537846638821065e-05,
        2.774007589323446e-05
      ],
      "linear_speed_mps": 0.009452934510549014,
      "local_corner_max_m": [
        0.04362523217186562,
        0.07823037100715113,
        -0.02007889836033977
      ],
      "local_corner_min_m": [
        -0.05304143294634461,
        0.0009420456964089885,
        -0.09711862037718427
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019632217928067186,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05815207893648944,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018887643080355065,
      "step_index": 2292,
      "timestamp_seconds": 9.168000435456634,
      "trace_row": 2292,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02082334961709237,
      "vertical_lower_margin_m": -0.02082334961709237,
      "vertical_upper_margin_m": 0.026535024306350227
    },
    {
      "actual_left_finger_qpos_m": [
        0.02275732345879078,
        0.022466111928224564
      ],
      "angular_speed_rps": 0.420190292585158,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 44,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004708711228151918,
        0.03958576657850654,
        -0.05856013910831381
      ],
      "can_pose": [
        -0.3485836386680603,
        -0.15714119374752045,
        0.8195894360542297,
        -0.00013114162720739841,
        -0.10164135694503784,
        0.000555360980797559,
        0.9948211312294006
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7565185940160606,
      "can_relative_translation_from_partial_start_m": [
        -0.003766179084777832,
        -0.12352573871612549,
        -0.05702704191207886
      ],
      "can_to_box_relative_orientation_rad": 2.2152178792795296,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -8.513884677086025e-05,
        2.3039337975205854e-05
      ],
      "linear_speed_mps": 0.009644206306744774,
      "local_corner_max_m": [
        0.04362370074670241,
        0.07818631160748168,
        -0.02008272849950765
      ],
      "local_corner_min_m": [
        -0.053041123203006246,
        0.000985221549531401,
        -0.09703754971711998
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019670838188515394,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058148248797321556,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018806572420290768,
      "step_index": 2293,
      "timestamp_seconds": 9.172000435646623,
      "trace_row": 2293,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02078017376396996,
      "vertical_lower_margin_m": -0.02078017376396996,
      "vertical_upper_margin_m": 0.026579083706019677
    },
    {
      "actual_left_finger_qpos_m": [
        0.022756613790988922,
        0.02246631681919098
      ],
      "angular_speed_rps": 0.42894111394158413,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 43,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004709202832016701,
        0.039585151142145,
        -0.05852085669606605
      ],
      "can_pose": [
        -0.3485444188117981,
        -0.15714168548583984,
        0.8195899724960327,
        -0.00013116125774104148,
        -0.1007879450917244,
        0.0005435507046058774,
        0.994907796382904
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7548074296743774,
      "can_relative_translation_from_partial_start_m": [
        -0.003766670823097229,
        -0.12352520227432251,
        -0.05698782205581665
      ],
      "can_to_box_relative_orientation_rad": 2.2141800076043716,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -6.860244320705533e-05,
        3.1976524041965604e-05
      ],
      "linear_speed_mps": 0.009806651299754875,
      "local_corner_max_m": [
        0.043622347388569044,
        0.07814114837308306,
        -0.020086887837836076
      ],
      "local_corner_min_m": [
        -0.053040753052602474,
        0.001029153911206948,
        -0.09695482555429602
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01971012060076316,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05814408945899313,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018723848257466813,
      "step_index": 2294,
      "timestamp_seconds": 9.176000435836613,
      "trace_row": 2294,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020736241402294412,
      "vertical_lower_margin_m": -0.020736241402294412,
      "vertical_upper_margin_m": 0.026624246940418303
    },
    {
      "actual_left_finger_qpos_m": [
        0.02275584265589714,
        0.022466517984867096
      ],
      "angular_speed_rps": 0.43816936146970886,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 43,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004709858292992863,
        0.03958455108982406,
        -0.05848065238090899
      ],
      "can_pose": [
        -0.34850427508354187,
        -0.15714234113693237,
        0.8195907473564148,
        -0.00013095980102661997,
        -0.09991616010665894,
        0.0005294150905683637,
        0.9949958920478821
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7530597616385697,
      "can_relative_translation_from_partial_start_m": [
        -0.0037673264741897583,
        -0.12352442741394043,
        -0.056947678327560425
      ],
      "can_to_box_relative_orientation_rad": 2.213122394471402,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00011927396553801373,
        3.4149186831200495e-05
      ],
      "linear_speed_mps": 0.010039139193964144,
      "local_corner_max_m": [
        0.04362065209226251,
        0.07809472542704599,
        -0.020091178403213006
      ],
      "local_corner_min_m": [
        -0.05304036867824824,
        0.0010743767526021353,
        -0.09687012635860498
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019750324915920214,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.0581397988936162,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018639149061775773,
      "step_index": 2295,
      "timestamp_seconds": 9.180000436026603,
      "trace_row": 2295,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020691018560899225,
      "vertical_lower_margin_m": -0.020691018560899225,
      "vertical_upper_margin_m": 0.026670669886455375
    },
    {
      "actual_left_finger_qpos_m": [
        0.022755036130547523,
        0.022466715425252914
      ],
      "angular_speed_rps": 0.4491223798431101,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 42,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004710483912327812,
        0.03958380502182057,
        -0.058439276281678665
      ],
      "can_pose": [
        -0.3484629690647125,
        -0.15714296698570251,
        0.8195913434028625,
        -0.00013093282177578658,
        -0.09902247041463852,
        0.0005156183615326881,
        0.9950851798057556
      ],
      "can_relative_orientation_from_partial_start_rad": 1.751268313140812,
      "can_relative_translation_from_partial_start_m": [
        -0.0037679523229599,
        -0.12352383136749268,
        -0.05690637230873108
      ],
      "can_to_box_relative_orientation_rad": 2.2120382646077257,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00013805013441015035,
        3.882237069774419e-05
      ],
      "linear_speed_mps": 0.010328764408894698,
      "local_corner_max_m": [
        0.04361902186878647,
        0.07804695579217513,
        -0.020095524167073553
      ],
      "local_corner_min_m": [
        -0.05303998969344209,
        0.0011206542514660134,
        -0.09678302839628378
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019791701015150542,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058135453129755654,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01855205109945457,
      "step_index": 2296,
      "timestamp_seconds": 9.184000436216593,
      "trace_row": 2296,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020644741062035347,
      "vertical_lower_margin_m": -0.020644741062035347,
      "vertical_upper_margin_m": 0.02671843952132623
    },
    {
      "actual_left_finger_qpos_m": [
        0.02275431528687477,
        0.02246692031621933
      ],
      "angular_speed_rps": 0.46185461460687116,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 43,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.00471110949003864,
        0.03958305050092936,
        -0.058396942367688276
      ],
      "can_pose": [
        -0.3484207093715668,
        -0.15714359283447266,
        0.8195919394493103,
        -0.00013098446652293205,
        -0.098103366792202,
        0.0005017362418584526,
        0.9951762557029724
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7494260420991672,
      "can_relative_translation_from_partial_start_m": [
        -0.0037685781717300415,
        -0.12352323532104492,
        -0.05686411261558533
      ],
      "can_to_box_relative_orientation_rad": 2.2109236781661705,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        2.119129931088537e-06,
        2.243261769763194e-05
      ],
      "linear_speed_mps": 0.010567131981714228,
      "local_corner_max_m": [
        0.043617391046243265,
        0.07799774491693123,
        -0.020100335293455673
      ],
      "local_corner_min_m": [
        -0.053039610026320516,
        0.001168356084927491,
        -0.09669354944192088
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01983403492914093,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058130642003373534,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01846257214509167,
      "step_index": 2297,
      "timestamp_seconds": 9.188000436406583,
      "trace_row": 2297,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02059703922857387,
      "vertical_lower_margin_m": -0.02059703922857387,
      "vertical_upper_margin_m": 0.026767650396570128
    },
    {
      "actual_left_finger_qpos_m": [
        0.022753605619072914,
        0.02246711775660515
      ],
      "angular_speed_rps": 0.47501151174475265,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 43,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004711764816670294,
        0.03958207027149019,
        -0.05835328759267894
      ],
      "can_pose": [
        -0.34837713837623596,
        -0.15714424848556519,
        0.8195923566818237,
        -0.00013113410386722535,
        -0.09715798497200012,
        0.00048736127791926265,
        0.9952689409255981
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7475313142537927,
      "can_relative_translation_from_partial_start_m": [
        -0.003769233822822571,
        -0.1235228180885315,
        -0.05682054162025452
      ],
      "can_to_box_relative_orientation_rad": 2.2097781274150634,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -4.54910405096598e-05,
        3.014918911503628e-05
      ],
      "linear_speed_mps": 0.010894480870618107,
      "local_corner_max_m": [
        0.043615702037544,
        0.07794678269197997,
        -0.020105297178292014
      ],
      "local_corner_min_m": [
        -0.05303923167088459,
        0.0012173578510004113,
        -0.09660127800706586
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01987768970415027,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05812568011853719,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018370300710236653,
      "step_index": 2298,
      "timestamp_seconds": 9.192000436596572,
      "trace_row": 2298,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02054803746250095,
      "vertical_lower_margin_m": -0.02054803746250095,
      "vertical_upper_margin_m": 0.026818612621521395
    },
    {
      "actual_left_finger_qpos_m": [
        0.022752854973077774,
        0.02246733196079731
      ],
      "angular_speed_rps": 0.4903088897367679,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 42,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004712420139186213,
        0.03958100147949151,
        -0.0583083797394961
      ],
      "can_pose": [
        -0.3483322262763977,
        -0.15714490413665771,
        0.8195927143096924,
        -0.00013038476754445583,
        -0.09618207812309265,
        0.0004727815103251487,
        0.9953638315200806
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7455755257204617,
      "can_relative_translation_from_partial_start_m": [
        -0.0037698894739151,
        -0.12352246046066284,
        -0.05677562952041626
      ],
      "can_to_box_relative_orientation_rad": 2.2085949855619416,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00013394591223914176,
        3.4848530049202964e-05
      ],
      "linear_speed_mps": 0.011229576729173288,
      "local_corner_max_m": [
        0.04361394686248471,
        0.07789399308447964,
        -0.020110808636136124
      ],
      "local_corner_min_m": [
        -0.053038787140857135,
        0.001268009874503373,
        -0.09650595084285607
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.01992259755733311,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05812016866069308,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018274973546026863,
      "step_index": 2299,
      "timestamp_seconds": 9.196000436786562,
      "trace_row": 2299,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020497385438997987,
      "vertical_lower_margin_m": -0.020497385438997987,
      "vertical_upper_margin_m": 0.02687140222902172
    },
    {
      "actual_left_finger_qpos_m": [
        0.022752122953534126,
        0.02246752567589283
      ],
      "angular_speed_rps": 0.5064649479232826,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 42,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0047131498875735145,
        0.039579801322524366,
        -0.05826195074467927
      ],
      "can_pose": [
        -0.3482857942581177,
        -0.1571456342935562,
        0.819593071937561,
        -0.0001295711554121226,
        -0.0951739102602005,
        0.0004568335716612637,
        0.9954606294631958
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7435554338978871,
      "can_relative_translation_from_partial_start_m": [
        -0.0037706196308135986,
        -0.12352210283279419,
        -0.05672919750213623
      ],
      "can_to_box_relative_orientation_rad": 2.2073744709565375,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -9.056513954419643e-05,
        3.1705327273812145e-05
      ],
      "linear_speed_mps": 0.011609783437580986,
      "local_corner_max_m": [
        0.043612017164248756,
        0.07783912822415295,
        -0.020116612358599295
      ],
      "local_corner_min_m": [
        -0.05303831693939581,
        0.0013204744208957786,
        -0.09640728913075924
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.019969026552149938,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05811436493822991,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.018176311833930037,
      "step_index": 2300,
      "timestamp_seconds": 9.200000436976552,
      "trace_row": 2300,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02044492089260558,
      "vertical_lower_margin_m": -0.02044492089260558,
      "vertical_upper_margin_m": 0.026926267089348407
    },
    {
      "actual_left_finger_qpos_m": [
        0.02275129035115242,
        0.0224677175283432
      ],
      "angular_speed_rps": 0.524063514344774,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 42,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004713849807650411,
        0.03957851420772651,
        -0.05821387549630991
      ],
      "can_pose": [
        -0.3482377231121063,
        -0.15714633464813232,
        0.8195932507514954,
        -0.00012898404384031892,
        -0.09413060545921326,
        0.0004418482421897352,
        0.9955599308013916
      ],
      "can_relative_orientation_from_partial_start_rad": 1.741464935955927,
      "can_relative_translation_from_partial_start_m": [
        -0.0037713199853897095,
        -0.12352192401885986,
        -0.05668112635612488
      ],
      "can_to_box_relative_orientation_rad": 2.206110798864984,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00013635423965752125,
        2.5655856006778777e-05
      ],
      "linear_speed_mps": 0.012019144442911156,
      "local_corner_max_m": [
        0.04361020003504906,
        0.07778229320475172,
        -0.02012274330457653
      ],
      "local_corner_min_m": [
        -0.053037899650349885,
        0.0013747352107013056,
        -0.09630500768804329
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.0200171018005193,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05810823399225268,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01807403039121408,
      "step_index": 2301,
      "timestamp_seconds": 9.204000437166542,
      "trace_row": 2301,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020390660102800055,
      "vertical_lower_margin_m": -0.020390660102800055,
      "vertical_upper_margin_m": 0.026983102108749643
    },
    {
      "actual_left_finger_qpos_m": [
        0.022750472649931908,
        0.022467918694019318
      ],
      "angular_speed_rps": 0.5434897847554057,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 42,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004714609238791023,
        0.03957702124282292,
        -0.0581641347531468
      ],
      "can_pose": [
        -0.34818798303604126,
        -0.1571470946073532,
        0.8195933699607849,
        -0.00012828152102883905,
        -0.09304851293563843,
        0.0004253453516867012,
        0.9956615567207336
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7392970986053355,
      "can_relative_translation_from_partial_start_m": [
        -0.0037720799446105957,
        -0.12352180480957031,
        -0.056631386280059814
      ],
      "can_to_box_relative_orientation_rad": 2.2048020205589247,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -3.675605694297701e-05,
        1.9731229258468375e-05
      ],
      "linear_speed_mps": 0.012436505439505755,
      "local_corner_max_m": [
        0.0436082099766808,
        0.07772292337591435,
        -0.020129397662286108
      ],
      "local_corner_min_m": [
        -0.05303742845426285,
        0.0014311191097314824,
        -0.0961988718440075
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020066842543682406,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.0581015796345431,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017967894547178287,
      "step_index": 2302,
      "timestamp_seconds": 9.208000437356532,
      "trace_row": 2302,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020334276203769878,
      "vertical_lower_margin_m": -0.020334276203769878,
      "vertical_upper_margin_m": 0.027042471937587007
    },
    {
      "actual_left_finger_qpos_m": [
        0.022749722003936768,
        0.022468123584985733
      ],
      "angular_speed_rps": 0.5637655188333253,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 41,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004715353696889413,
        0.039575377077539775,
        -0.05811238702567606
      ],
      "can_pose": [
        -0.3481362462043762,
        -0.1571478396654129,
        0.8195933699607849,
        -0.000127725419588387,
        -0.09192594885826111,
        0.00040850756340660155,
        0.9957659244537354
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7370483589464185,
      "can_relative_translation_from_partial_start_m": [
        -0.003772825002670288,
        -0.12352180480957031,
        -0.056579649448394775
      ],
      "can_to_box_relative_orientation_rad": 2.203445095245841,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -1.1271273251622915e-05,
        1.6532503650523722e-05
      ],
      "linear_speed_mps": 0.012935548422668815,
      "local_corner_max_m": [
        0.043606221038063026,
        0.07766108091556168,
        -0.0201363285827586
      ],
      "local_corner_min_m": [
        -0.05303692843184188,
        0.0014896732395178747,
        -0.09608844546859352
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020118590271153147,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05809464871407061,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017857468171764312,
      "step_index": 2303,
      "timestamp_seconds": 9.212000437546521,
      "trace_row": 2303,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020275722073983485,
      "vertical_lower_margin_m": -0.020275722073983485,
      "vertical_upper_margin_m": 0.027104314397939686
    },
    {
      "actual_left_finger_qpos_m": [
        0.02274898625910282,
        0.02246832847595215
      ],
      "angular_speed_rps": 0.5861767558557346,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 42,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004716172593372536,
        0.039573528520320256,
        -0.05805866200458576
      ],
      "can_pose": [
        -0.3480824828147888,
        -0.15714865922927856,
        0.8195932507514954,
        -0.00012664904352277517,
        -0.09075862169265747,
        0.00039083618321456015,
        0.9958729147911072
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7347102561797068,
      "can_relative_translation_from_partial_start_m": [
        -0.0037736445665359497,
        -0.12352192401885986,
        -0.05652588605880737
      ],
      "can_to_box_relative_orientation_rad": 2.202034728758438,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -3.37206874974072e-05,
        2.4257078621303663e-05
      ],
      "linear_speed_mps": 0.013442441372996846,
      "local_corner_max_m": [
        0.04360406940179981,
        0.07759641559078512,
        -0.020143869763024347
      ],
      "local_corner_min_m": [
        -0.053036414588544856,
        0.0015506414498553944,
        -0.09597345424614717
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020172315292243448,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05808710753380486,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017742476949317965,
      "step_index": 2304,
      "timestamp_seconds": 9.216000437736511,
      "trace_row": 2304,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020214753863645966,
      "vertical_lower_margin_m": -0.020214753863645966,
      "vertical_upper_margin_m": 0.027168979722716244
    },
    {
      "actual_left_finger_qpos_m": [
        0.02274828962981701,
        0.022468527778983116
      ],
      "angular_speed_rps": 0.6099448417473322,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 41,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004716991395378262,
        0.039571480937120485,
        -0.058002776187365046
      ],
      "can_pose": [
        -0.3480266034603119,
        -0.15714947879314423,
        0.8195929527282715,
        -0.00012610644625965506,
        -0.08954384177923203,
        0.0003729215241037309,
        0.9959830045700073
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7322772999043194,
      "can_relative_translation_from_partial_start_m": [
        -0.0037744641304016113,
        -0.12352222204208374,
        -0.056470006704330444
      ],
      "can_to_box_relative_orientation_rad": 2.200568228808606,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -1.7162652511615306e-05,
        2.392535679973662e-05
      ],
      "linear_speed_mps": 0.013971539067950112,
      "local_corner_max_m": [
        0.043601933631702505,
        0.07752883236231323,
        -0.02015190874235151
      ],
      "local_corner_min_m": [
        -0.05303591642245903,
        0.0016141295119277421,
        -0.09585364363237858
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02022820110946416,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.0580790685544777,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017622666335549375,
      "step_index": 2305,
      "timestamp_seconds": 9.220000437926501,
      "trace_row": 2305,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020151265801573618,
      "vertical_lower_margin_m": -0.020151265801573618,
      "vertical_upper_margin_m": 0.027236562951188134
    },
    {
      "actual_left_finger_qpos_m": [
        0.022747594863176346,
        0.022468727082014084
      ],
      "angular_speed_rps": 0.6353718853016984,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004717839867044077,
        0.03956936325443816,
        -0.057944496732888984
      ],
      "can_pose": [
        -0.34796833992004395,
        -0.15715032815933228,
        0.8195927143096924,
        -0.00012563198106363416,
        -0.08827826380729675,
        0.00035365234361961484,
        0.9960958361625671
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7297430269996326,
      "can_relative_translation_from_partial_start_m": [
        -0.0037753134965896606,
        -0.12352246046066284,
        -0.0564117431640625
      ],
      "can_to_box_relative_orientation_rad": 2.1990424169532985,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        9.676849003881216e-06,
        2.5105749955400825e-05
      ],
      "linear_speed_mps": 0.01456755399069113,
      "local_corner_max_m": [
        0.04359967821477334,
        0.07745814950424035,
        -0.020160448537548892
      ],
      "local_corner_min_m": [
        -0.053035357948861495,
        0.0016805770046359747,
        -0.09572854492822908
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020286480563940223,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.058070528759280315,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01749756763139987,
      "step_index": 2306,
      "timestamp_seconds": 9.22400043811649,
      "trace_row": 2306,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.020084818308865385,
      "vertical_lower_margin_m": -0.020084818308865385,
      "vertical_upper_margin_m": 0.027307245809261013
    },
    {
      "actual_left_finger_qpos_m": [
        0.022746911272406578,
        0.022468920797109604
      ],
      "angular_speed_rps": 0.6627644684434926,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 39,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.0047187627352301975,
        0.03956676228230549,
        -0.057883803464240546
      ],
      "can_pose": [
        -0.3479076623916626,
        -0.1571512520313263,
        0.8195920586585999,
        -0.00012519487063400447,
        -0.08695799112319946,
        0.0003337051020935178,
        0.9962120652198792
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7270994892912939,
      "can_relative_translation_from_partial_start_m": [
        -0.003776237368583679,
        -0.12352311611175537,
        -0.05635106563568115
      ],
      "can_to_box_relative_orientation_rad": 2.1974518356397907,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -7.51188417780213e-05,
        3.836058749584481e-05
      ],
      "linear_speed_mps": 0.015172025075808022,
      "local_corner_max_m": [
        0.04359730479724827,
        0.07738378144603153,
        -0.020169716104255497
      ],
      "local_corner_min_m": [
        -0.053034830267708666,
        0.0017497431185794499,
        -0.0955978908242256
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.02034717383258866,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05806126119257371,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017366913527396388,
      "step_index": 2307,
      "timestamp_seconds": 9.22800043830648,
      "trace_row": 2307,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.02001565219492191,
      "vertical_lower_margin_m": -0.02001565219492191,
      "vertical_upper_margin_m": 0.02738161386746983
    },
    {
      "actual_left_finger_qpos_m": [
        0.022746188566088676,
        0.022469116374850273
      ],
      "angular_speed_rps": 0.691702784184834,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004719685464101814,
        0.03956395358874465,
        -0.05782035060800522
      ],
      "can_pose": [
        -0.3478442430496216,
        -0.1571521759033203,
        0.8195912837982178,
        -0.00012497177522163838,
        -0.08557989448308945,
        0.0003128288662992418,
        0.9963313341140747
      ],
      "can_relative_orientation_from_partial_start_rad": 1.724340556836434,
      "can_relative_translation_from_partial_start_m": [
        -0.0037771612405776978,
        -0.12352389097213745,
        -0.05628764629364014
      ],
      "can_to_box_relative_orientation_rad": 2.195793357413226,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -3.45100270351395e-05,
        2.3245331249199808e-05
      ],
      "linear_speed_mps": 0.015857700240694505,
      "local_corner_max_m": [
        0.04359488101077008,
        0.07730578488459483,
        -0.020179543820946888
      ],
      "local_corner_min_m": [
        -0.05303425193897371,
        0.001822122292894468,
        -0.09546115739506356
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020410626688823985,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05805143347588232,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.01723018009823435,
      "step_index": 2308,
      "timestamp_seconds": 9.23200043849647,
      "trace_row": 2308,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019943273020606892,
      "vertical_lower_margin_m": -0.019943273020606892,
      "vertical_upper_margin_m": 0.02745961042890653
    },
    {
      "actual_left_finger_qpos_m": [
        0.022745424881577492,
        0.02246931754052639
      ],
      "angular_speed_rps": 0.7239935887344399,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00015590168186463416,
        3.841984653263353e-05
      ],
      "linear_speed_mps": 0.016602695290689955,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2309,
      "timestamp_seconds": 9.23600043868646,
      "trace_row": 2309,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.02274465374648571,
        0.02246950939297676
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -6.410010973922908e-05,
        2.5629815354477614e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2310,
      "timestamp_seconds": 9.24000043887645,
      "trace_row": 2310,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.0227439496666193,
        0.02246970310807228
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        3.938961890526116e-05,
        1.665897434577346e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2311,
      "timestamp_seconds": 9.24400043906644,
      "trace_row": 2311,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.022743187844753265,
        0.02246990241110325
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -0.00012113324919482693,
        2.999253774760291e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2312,
      "timestamp_seconds": 9.24800043925643,
      "trace_row": 2312,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.022742407396435738,
        0.022470103576779366
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -8.60378349898383e-06,
        1.912999141495675e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2313,
      "timestamp_seconds": 9.25200043944642,
      "trace_row": 2313,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.02274170331656933,
        0.022470304742455482
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -5.240934115136042e-05,
        3.1615149055141956e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2314,
      "timestamp_seconds": 9.25600043963641,
      "trace_row": 2314,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.022740960121154785,
        0.02247050032019615
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -6.736881914548576e-05,
        2.6760670152725652e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2315,
      "timestamp_seconds": 9.260000439826399,
      "trace_row": 2315,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.022740254178643227,
        0.022470686584711075
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -2.0022634998895228e-05,
        2.9582810384454206e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2316,
      "timestamp_seconds": 9.264000440016389,
      "trace_row": 2316,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.02273964136838913,
        0.022470887750387192
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -3.712711622938514e-05,
        2.94226520054508e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2317,
      "timestamp_seconds": 9.268000440206379,
      "trace_row": 2317,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.022738885134458542,
        0.022471077740192413
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        2.2675187210552394e-05,
        1.1744046787498519e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2318,
      "timestamp_seconds": 9.272000440396369,
      "trace_row": 2318,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.0227382630109787,
        0.02247127704322338
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        2.1359861420933157e-05,
        2.184011827921495e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2319,
      "timestamp_seconds": 9.276000440586358,
      "trace_row": 2319,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.02273758314549923,
        0.022471459582448006
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        -8.845276897773147e-05,
        3.980529072578065e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2320,
      "timestamp_seconds": 9.280000440776348,
      "trace_row": 2320,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    },
    {
      "actual_left_finger_qpos_m": [
        0.022736890241503716,
        0.02247164584696293
      ],
      "angular_speed_rps": 0.0,
      "box_contact": {
        "evidence_complete": true,
        "pair_count": 40,
        "physical_hit": true
      },
      "can_geometry_center_box_local_m": [
        -0.004720890899843927,
        0.03956122147209218,
        -0.057753908807932575
      ],
      "can_pose": [
        -0.3477778434753418,
        -0.15715338289737701,
        0.8195911049842834,
        -0.00012450056965462863,
        -0.08413737267255783,
        0.0002865202259272337,
        0.9964542388916016
      ],
      "can_relative_orientation_from_partial_start_rad": 1.7214535296390618,
      "can_relative_translation_from_partial_start_m": [
        -0.0037783682346343994,
        -0.12352406978607178,
        -0.05622124671936035
      ],
      "can_to_box_relative_orientation_rad": 2.194063631702921,
      "finger_contact": {
        "evidence_complete": false,
        "pair_count": 0,
        "physical_hit": false
      },
      "left_finger_drive_target_m": [
        0.022540278732776642,
        0.022540278732776642
      ],
      "left_finger_qf_audit_only": [
        6.807888031005859,
        -6.807892322540283
      ],
      "left_finger_qvel_mps": [
        6.681293598376215e-07,
        2.753386797849089e-05
      ],
      "linear_speed_mps": 0.0,
      "local_corner_max_m": [
        0.043591779672680186,
        0.07722361845543668,
        -0.020190100735421546
      ],
      "local_corner_min_m": [
        -0.05303356147236804,
        0.0018988244887476746,
        -0.0953177168804436
      ],
      "opening_center_inside": true,
      "opening_center_signed_margin_m": 0.020477068488896633,
      "opening_projection_inside": false,
      "opening_projection_overlap_signed_m": 0.05804087656140766,
      "opening_projection_overlaps": true,
      "opening_projection_signed_margin_m": -0.017086739583614396,
      "step_index": 2321,
      "timestamp_seconds": 9.284000440966338,
      "trace_row": 2321,
      "true_cavity_obb": false,
      "true_cavity_signed_margin_m": -0.019866570824753686,
      "vertical_lower_margin_m": -0.019866570824753686,
      "vertical_upper_margin_m": 0.02754177685806468
    }
  ]
}
```
