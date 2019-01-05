import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

#blacklist = ['doug205', 'doug246', 'doug258', 'doug257', 'doug247', 'doug250', 'doug255']
whitelist = ['doug196', 'doug198','doug200','doug201','doug210','doug211','doug212','doug213','doug216','doug217','doug219','doug220','doug221','doug223','doug229','doug236','doug237','doug240','doug248','doug251','doug253','doug263']

with open('faceColors.json', 'r') as f:
    faceColors = f.read()
    faceColors = json.loads(faceColors)

size = 10

lightnessFluxish = []
correctedLightnessFluxish = []

for (imageName, faceColor) in faceColors:
    #if imageName in blacklist:
    if imageName not in whitelist:
        continue
    print('Face Color ' + imageName + ' :: ' +str(faceColor))

    [fullFlash, halfFlash, corrected, fluxish] = faceColor
    lightnessFluxish.append(np.array([float(fullFlash[1]), float(fluxish)]))
    correctedLightnessFluxish.append(np.array([float(corrected[1]), float(fluxish)]))

lightnessFluxish = np.array(lightnessFluxish)
correctedLightnessFluxish = np.array(correctedLightnessFluxish)

minFluxish = min(lightnessFluxish[:, 1])
maxFluxish = max(lightnessFluxish[:, 1])

fluxish_A = np.vstack([lightnessFluxish[:, 1], np.ones(len(lightnessFluxish))]).T

FL_m, FL_c = np.linalg.lstsq(fluxish_A, lightnessFluxish[:, 0], rcond=None)[0]
print('Fluxish to Lightness Slope, Constant :: ' + str(FL_m) + ' ' + str(FL_c))
plt.plot([minFluxish, maxFluxish], [(FL_m * minFluxish + FL_c), (FL_m * maxFluxish + FL_c)])

plt.scatter(lightnessFluxish[:, 1], lightnessFluxish[:, 0], size, (1, 0, 0))

plt.xlabel('Fluxish')
plt.ylabel('Lightness')
plt.suptitle("Fluxish vs Lightness")
#plt.show()

plt.scatter(correctedLightnessFluxish[:, 1], correctedLightnessFluxish[:, 0], size, (0, 1, 0))

#plt.xlabel('Fluxish')
#plt.ylabel('Lightness')
#plt.suptitle("Corrected Fluxish vs Lightness")
plt.show()
