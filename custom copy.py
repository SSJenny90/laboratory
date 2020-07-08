import numpy as np
import matplotlib.pyplot as plt
import time

time.sleep
thermopower = True

middle = 5000

grad = np.abs(np.array([-3.2,-2.1,-1.4,0.1,1.3,2.5,3.4]))

print(grad)
print(grad-2)
idx = (np.abs(grad-2)).argmin()
print(idx)
print(grad[idx])


# if thermopower:
#     gradient = 10
#     est_position_for_gradient = 4500
#     travel = middle - est_position_for_gradient

#     steps = np.linspace(middle,est_position_for_gradient,10).astype(int)
#     steps = np.concatenate((steps,np.flipud(steps)))

#     est_upper_position = middle + travel 

#     more = np.linspace(middle,est_upper_position,10).astype(int)
#     more = np.concatenate((more,np.flipud(more)))

#     all_steps = np.concatenate((steps[:-1],more[:-1]))

#     print(len(all_steps))
#     total_time = 0
#     for step in all_steps:
#         # print('moving stage to {}'.format(step))
#         # wait x amount of minutes before starting measurements
#         # print('waiting 10 minutes for equilibration')
#         total_time += 10
#         # print('taking 20 measurements at position {}'.format(step))

#     print('time spent taking measurements: {}'.format(total_time/60))


#     steps = np.linspace(middle,est_position_for_gradient,10).astype(int)
#     more = np.linspace(middle,est_upper_position,10).astype(int)

#     all_steps = np.concatenate((steps, more))
#     print(len(all_steps))

#     total_time = 0
#     for step in all_steps:
#         # print('moving stage to {}'.format(step))
#         # wait x amount of minutes before starting measurements
#         # print('waiting 10 minutes for equilibration')
#         total_time += 10
#         # print('taking 20 measurements at position {}'.format(step))

#     print('time spent taking measurements: {}'.format(total_time/60))

#     # print(more)


#     # for i in all_steps:
#         # print(i)

#     # plt.figure()
#     # plt.plot(all_steps,'rx')
#     # plt.show()
#     # print(steps)
