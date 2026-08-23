package afdxtest.networks.simpleNetwork;

import afdx.EndSystem;
import afdx.Switch;
import afdx.Cable;

//
// AFDX network from docs/topology.png (Figure 6.1) and docs/virtual-link-description.png
// (Table 6.1), built as a dual-redundant AFDX network (plane A / plane B), per the afdx
// library's EndSystem/Switch model.
//
// End system index:  0=E0 1=E1 2=E2 3=E3 4=E4 5=E5 6=E6
// Switch index:       0=S1 1=S2 2=S3 3=S4 4=S5   (SwitchA = plane A, SwitchB = plane B)
//
// Per-instance noOfPorts / messageCount and all VL parameters are set in simpleNetwork.ini.
//
network simpleNetwork
{
    submodules:
        ES[7]: afdx.EndSystem;
        SwitchA[5]: afdx.Switch;
        SwitchB[5]: afdx.Switch;

    connections:
        // ---- Plane A ----
        ES[0].ethPortA <--> afdx.Cable <--> SwitchA[0].ethPort[0]; // E0 - S1
        ES[1].ethPortA <--> afdx.Cable <--> SwitchA[0].ethPort[1]; // E1 - S1
        SwitchA[0].ethPort[2] <--> afdx.Cable <--> SwitchA[1].ethPort[0]; // S1 - S2
        SwitchA[0].ethPort[3] <--> afdx.Cable <--> SwitchA[2].ethPort[0]; // S1 - S3
        SwitchA[2].ethPort[1] <--> afdx.Cable <--> ES[4].ethPortA; // S3 - E4
        SwitchA[2].ethPort[2] <--> afdx.Cable <--> ES[5].ethPortA; // S3 - E5
        SwitchA[1].ethPort[1] <--> afdx.Cable <--> SwitchA[3].ethPort[0]; // S2 - S4
        SwitchA[1].ethPort[2] <--> afdx.Cable <--> ES[3].ethPortA; // S2 - E3
        SwitchA[3].ethPort[1] <--> afdx.Cable <--> SwitchA[4].ethPort[0]; // S4 - S5
        SwitchA[3].ethPort[2] <--> afdx.Cable <--> ES[2].ethPortA; // S4 - E2
        SwitchA[4].ethPort[1] <--> afdx.Cable <--> ES[6].ethPortA; // S5 - E6

        // ---- Plane B (redundant mirror of plane A) ----
        ES[0].ethPortB <--> afdx.Cable <--> SwitchB[0].ethPort[0]; // E0 - S1
        ES[1].ethPortB <--> afdx.Cable <--> SwitchB[0].ethPort[1]; // E1 - S1
        SwitchB[0].ethPort[2] <--> afdx.Cable <--> SwitchB[1].ethPort[0]; // S1 - S2
        SwitchB[0].ethPort[3] <--> afdx.Cable <--> SwitchB[2].ethPort[0]; // S1 - S3
        SwitchB[2].ethPort[1] <--> afdx.Cable <--> ES[4].ethPortB; // S3 - E4
        SwitchB[2].ethPort[2] <--> afdx.Cable <--> ES[5].ethPortB; // S3 - E5
        SwitchB[1].ethPort[1] <--> afdx.Cable <--> SwitchB[3].ethPort[0]; // S2 - S4
        SwitchB[1].ethPort[2] <--> afdx.Cable <--> ES[3].ethPortB; // S2 - E3
        SwitchB[3].ethPort[1] <--> afdx.Cable <--> SwitchB[4].ethPort[0]; // S4 - S5
        SwitchB[3].ethPort[2] <--> afdx.Cable <--> ES[2].ethPortB; // S4 - E2
        SwitchB[4].ethPort[1] <--> afdx.Cable <--> ES[6].ethPortB; // S5 - E6
}
