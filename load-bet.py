import originpro as op
import os
import re


def extractBETData(path, **kwargs):
    fileContents = open(path).read()
    
    
    data = {
        'path': os.path.dirname(path),
        'filename': os.path.basename(path)
    }
    
    p = re.compile(r'^== (.+?) ==((?:\r?\n(?!== ).*)*)', re.M)
    for match in p.findall(fileContents):
        
        # == Isotherm ==
        if match[0] == 'Isotherm':
            data['isotherm'] = {
                'adsorption': {
                    'pres': [],
                    'vol': []
                },
                'desorption': {
                    'pres': [],
                    'vol': []
                }
            }
            lastpres = 0
            adsorptionTest = True
            for line in re.findall(r'^\ *(\S+) +(\S+)\s*$', match[1], re.M):
                linePres = float(line[0])
                lineVol = float(line[1])
                
                if adsorptionTest:
                    #check if still adsorption:
                    if linePres < lastpres:
                        adsorptionTest = False
                        
                    #store point to ADS
                    data['isotherm']['adsorption']['pres'].append(linePres)
                    data['isotherm']['adsorption']['vol'].append(lineVol)
                else:
                    #store point to DES
                    data['isotherm']['desorption']['pres'].append(linePres)
                    data['isotherm']['desorption']['vol'].append(lineVol)
                lastpres = linePres
                
        # == ^G Pore Size Distribution ==
        if match[0] == '^G Pore Size Distribution':
            data['pore-size'] = {
                'width': [],
                'Vol': [],
                'Surf': [],
                'dVol': [],
                'dSurf': []
            }
            for line in re.findall(r'^\ *([0-9\-\+\.e]+) +([0-9\-\+\.e]+) +([0-9\-\+\.e]+) +([0-9\-\+\.e]+) +([0-9\-\+\.e]+)\s*$', match[1], re.M):
                data['pore-size']['width'].append(float(line[0]))
                data['pore-size']['Vol'].append(float(line[1]))
                data['pore-size']['Surf'].append(float(line[2]))
                data['pore-size']['dVol'].append(float(line[3]))
                data['pore-size']['dSurf'].append(float(line[4]))
            
    return data
    
#tmp = op.file_dialog('*.txt')
#op.set_lt_str('fname', tmp)

fname = op.get_lt_str('fname')

data = extractBETData(fname)

wb = op.find_book()
wb.lname = data['filename']
wb.name = data['filename']

if 'isotherm' in data:
    adsorptionSht = wb.add_sheet('Adsorption')
    adsorptionSht.from_list(0, data['isotherm']['adsorption']['pres'], 'Pressure')
    adsorptionSht.from_list(1, data['isotherm']['adsorption']['vol'], 'Volume', 'cm\+3/g', 'Adsorption')

    desorptionSht = wb.add_sheet('Desorption')
    desorptionSht.from_list(0, data['isotherm']['desorption']['pres'], 'Pressure')
    desorptionSht.from_list(1, data['isotherm']['desorption']['vol'], 'Volume', 'cm\+3/g', 'Desorption')

    isothermGraph = op.new_graph(template='py-iso')
    isothermGraph.set_int('aa', 1)

    adsorptionPlt = isothermGraph[0].add_plot(adsorptionSht, coly=1, colx=0, type='y')
    adsorptionPlt.color = '#FA3C3C'
    desorptionPlt = isothermGraph[0].add_plot(desorptionSht, coly=1, colx=0, type='y')
    desorptionPlt.color = '#1E3CFF'

    isothermGraph[0].rescale()

if 'pore-size' in data:    
    DFTSht = wb.add_sheet('DFT')
    DFTSht.from_list(0, data['pore-size']['width'], 'Pore Diameter',            'nm',           '', 'X')
    DFTSht.from_list(1, data['pore-size']['Vol'],   'Cumulative Pore Volume',   'cm³/g',        '', 'Y')
    DFTSht.from_list(2, data['pore-size']['dVol'],  'd(V)',                     'cm³/g/nm',     '', 'Y')
    DFTSht.from_list(3, data['pore-size']['Surf'],  'Cumulative Surface Area',  'cm²/g',        '', 'Y')
    DFTSht.from_list(4, data['pore-size']['dSurf'], 'd(S)',                     'cm²/g/nm',     '', 'Y')
    
    poreVolGraph = op.new_graph(template='py-phys-vol')
    poreVolGraph.set_int('aa', 1)
    
    cumPoreVolPlt = poreVolGraph[0].add_plot(DFTSht, colx=0, coly=1, type='y')
    cumPoreVolPlt.color = '#FA3C3C'
    
    dVPlt = poreVolGraph[1].add_plot(DFTSht, colx=0, coly=2, type='y')
    dVPlt.color = '#1E3CFF'
    
    poreVolGraph[0].rescale()
    poreVolGraph[1].rescale()
    
#wb.lt_exec('layer -d 1;')