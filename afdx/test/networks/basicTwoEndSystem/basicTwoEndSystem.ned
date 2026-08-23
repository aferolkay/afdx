package afdxtest.networks.basicTwoEndSystem;

import afdx.EndSystem;
import afdx.Switch;
import afdx.Cable;

network basicTwoEndSystem
{
    parameters:

    types:

    submodules:
        // End Systems vector array
        ES[2]: afdx.EndSystem;

        // Grouped switches into a vector array of size 2 to satisfy getIndex()
        Switch[2]: afdx.Switch {
            noOfPorts = 2;
        };
	
    connections:
        // Redundancy Path A (SwitchA becomes Switch[0])
        ES[0].ethPortA <--> afdx.Cable <--> Switch[0].ethPort[0];
        Switch[0].ethPort[1] <--> afdx.Cable <--> ES[1].ethPortA;
		
        // Redundancy Path B (SwitchB becomes Switch[1])
        ES[0].ethPortB <--> afdx.Cable <--> Switch[1].ethPort[0];
        Switch[1].ethPort[1] <--> afdx.Cable <--> ES[1].ethPortB;
}