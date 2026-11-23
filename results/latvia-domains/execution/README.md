# Overnight scan execution

The scan began with one solver per case. The scheduler later ran up to two independent cases at once on separate physical performance cores of an Intel Core i7-1355U. Each solver used one computation thread and the frozen input, rule, search, memory and 60-second wall-time settings. On battery power the scheduler admitted one case at a time. After loss of mains power an already running pair could finish together. Each record committed before the switch was kept.

The two JSON files list the cases already complete at the switch and the start and finish times for subsequent cases. Overlapping intervals identify concurrent cases. A missing finish timestamp means the process was interrupted after persisting that case. Elapsed times, CPU turbo speeds and outcomes near the time limit can depend on concurrent load. Count proofs and resource limits in their recorded execution context. Each repaired result is matched to the SHA-256 hash of its original record.

The published launcher runs in the solver checkout identified in each manifest. The original scan and paired retry runners perform their usual input checks, produce the final counts and retain ownership of their completion markers.
