#!/usr/bin/env python3

import sys, json
from pysros.management import connect
from pysros.pprint import Table

credentials = {

    "port": 830,
}

# Fuction definition to output a SR OS style table to the screen
# for gRPC specific parameters
def print_grpc_subs_table(rows):

    # Define the columns that will be used in the table.  Each list item
    # is a tuple of (column width, heading).
    cols = [
        (5, "Id"),
        (72, "path"),
    ]

    # Initalize the Table object with the heading and columns.
    table = Table("of which the following are gRPC streaming telemetry subscriptions", cols, showCount='Subscriptions')

    # Print the output passing the data for the rows as an argument to the function.
    table.print(rows)

# Fuction definition to output a SR OS style table to the screen
# for TTM  specific parameters
def main():

# Initializing the grpc_info array already here to keep

# step 1: connect and retrieve grpc subscription
    c = connect()
    grpc_subs = c.running.get('/nokia-state:state/system/telemetry/grpc/subscription')
    grpc_info = []
    # d is required for splitting up paths longer than 50 chars
    d = []
    print("total subscription list :", list(grpc_subs.keys()))


# step 2: run through the list of subscriptions and retrieve the streaming ones
    for subscription in list(grpc_subs.keys()):

        subid = subscription
        grpc_path_list = grpc_subs[subscription]["path"]
        #print(list(grpc_path_list.keys()))

        for path in list(grpc_path_list.keys()):
            grpc_single_mode = grpc_path_list[path]["mode"]
            #print("path mode = ", grpc_single_mode)
            ## target-defined changed by sample, since may 2023
            ##expected_mode = "target-defined"
            expected_mode = "sample"

            if str(grpc_single_mode) == str(expected_mode):
                grpc_id = grpc_path_list[path]["path"]
                grpcid_str = str(grpc_id)
                #print("grpc_id length ", len(grpcid_str))

# step 3: chop the path in multiple lines if needed
                if len(grpcid_str) > 50:
                    d = []
                    d.append(grpcid_str.split("/"))
                    path_list = []
                    for el in d:
                        path_list =  path_list + el
                    #print(path_list)
                    counter = 0
                    grpc_partial = []
                    for path in path_list:
                        counter += 1
                        #print(path)
                        grpc_partial.append(path)
                        if counter > 2:
                            #make it a single string again
                            converted_list = [str(element) for element in grpc_partial]
                            s = "/"
                            s = s.join(converted_list)
                            #print("s =", s)
                            grpc_info.append([subid, s])
                            counter = 0
                            grpc_partial = ['    ']
                            subid = "  "
                    converted_list = [str(element) for element in grpc_partial]
                    s = "/"
                    s = s.join(converted_list)
                    #print("s =", s)
                    grpc_info.append([subid, s])
                else:
                # build the tables with single path line
                    grpc_info.append([subid, grpc_id])


# step 4: build the table
    print_grpc_subs_table(grpc_info)
if __name__ == "__main__":
    main()


