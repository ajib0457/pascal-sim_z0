import numpy as np
import h5py
from scipy.spatial import distance
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sklearn.preprocessing as skl
import sys
sys.path.insert(0, '/project/GAMNSCM2/funcs') 
from plotter_funcs import *
from error_func import *
import pickle
sim_type=sys.argv[1]   #'dm_only' 'DTFE'
cosmology=sys.argv[2]          #DMONLY:'lcdm'  'cde0'  'wdm2'DMGAS: 'lcdm' 'cde000' 'cde050' 'cde099'
snapshot=sys.argv[3]            #'12  '11'...
particles_filt=int(sys.argv[4])
den_type=sys.argv[5]      #'DTFE' 'my_den'
sim_sz=500           #Size of simulation in physical units Mpc/h cubed
grid_nodes=1250      #Density Field grid resolution
runs=20000
hist_bins=300
tot_dist_bins=9
sigma_area=0.3413    #sigma percentile area as decimal

f=h5py.File("/scratch/GAMNSCM2/%s/%s/snapshot_0%s/catalogs/%s_%s_snapshot_0%s_pascal_VELOCIraptor_allhalos_xyz_vxyz_jxyz_mtot_r_npart.h5"%(sim_type,cosmology,snapshot,sim_type,cosmology,snapshot), 'r')
#f=h5py.File("%s_%s_snapshot_0%s_pascal_VELOCIraptor_allhalos_xyz_vxyz_jxyz_mtot_r_npart.h5"%(sim_type,cosmology,snapshot), 'r')
data=f['/halo'][:]#halos array: (Pos)XYZ(Mpc/h), (Vel)VxVyVz(km/s), (Ang. Mom)JxJyJz((Msun/h)*(kpc/h)*km/s), (tot. Mass)Mtot(10^10Msun/h),(Vir. Rad)Rvir(kpc/h) & npart (no. particles for each sructure)
f.close()
#Filter out halos with N particles
partcl_halo_flt=np.where(data[:,11]>=particles_filt)#filter for halos with <N particles
data=data[partcl_halo_flt]#Filter out halos with <N particles

a_len=len(data)
#a_len=1000
dist_sp=distance.pdist(data[:,0:3], 'euclidean')
#dist_sp=distance.pdist(data[0:a_len,0:3], 'euclidean')

#range of halo-halo alignment signal
dist_min=10**(-1.2)
dist_max=10**0.8#Specific as Trowland+12 is.
#Filter out entire range to save memory
bn=np.logical_and(dist_sp>=dist_min,dist_sp<dist_max)
a=np.where(bn==True)
a=np.asarray(a)
log_dist=np.vstack((np.log10(dist_sp[a]),a))
del dist_sp
#log of distance and extremes
dist_min=np.min(log_dist[0,:])
dist_max=np.max(log_dist[0,:])
dist_intvl=(dist_max-dist_min)/tot_dist_bins#log_mass value used to find mass interval
results=np.zeros((tot_dist_bins,5))# [Mass_min, Mass_max, Value, Error+,Error-]
diction_2={}
for dist_bin in range(tot_dist_bins):
    
    low_int=dist_min+dist_intvl*dist_bin#Calculate mass interval
    hi_int=low_int+dist_intvl+0.000000001#Calculate mass interval
    results[dist_bin,0]=low_int#Store interval
    results[dist_bin,1]=hi_int#Store interval    
    bn=np.logical_and(log_dist[0,:]>=low_int,log_dist[0,:]<hi_int)
    a=np.where(bn==True)
    a=np.asarray(a)
    l,w=np.shape(a)

    #Find halos associated with distance range
    indxs=np.zeros((w))
    indxd=np.zeros((w))
    for j in range(w): 
        i=0
        div=log_dist[1,a[0,j]]-(a_len-1)    
        while div>=0:
            i+=1
            div=div-(a_len-1-i)
        indxs[j]=i    
        indxd[j]=indxs[j]+1+div+(a_len-1-i)
        
    indxs=indxs.astype(int)#the indices for the halos
    indxd=indxd.astype(int) 
    #Now take the dotproduct and then fit a line, make the 3 plots Trowland+13 makes.
    #normalize vectors
    vecs_indxs=skl.normalize(data[indxs,6:9])
    vecs_indxd=skl.normalize(data[indxd,6:9])
    #take dp
    store_dp=np.zeros(len(vecs_indxs))
    for i in range(len(vecs_indxs)):
        store_dp[i]=np.inner(vecs_indxs[i,:],vecs_indxd[i,:])#take the dot product between vecs, row by row   
    store_dp=abs(store_dp) 
    
    #method1: take average
    results[dist_bin,2]=np.mean(store_dp)
    #Calculating error using bootstrap resampling
    a=np.random.randint(low=0,high=len(store_dp),size=(runs,len(store_dp)))
    mean_set=np.mean(store_dp[a],axis=1)
    a=np.histogram(mean_set,density=True,bins=hist_bins)
    x=a[1]
    dx=(np.max(x)-np.min(x))/hist_bins
    x=np.delete(x,len(x)-1,0)+dx/2
    y=a[0]
    perc_lo,results[dist_bin,4],perc_hi,results[dist_bin,3],results[dist_bin,2],area=error(x,y,dx,sigma_area)
    diction_2[dist_bin]=mean_set
filehandler = open('/scratch/GAMNSCM2/halo_halo_plts/%s/%s/results_%s_%s_%s_%s.pkl'%(sim_type,cosmology,sim_type,cosmology,snapshot,particles_filt),"wb")       
pickle.dump(results,filehandler)
filehandler.close()

plt.figure()
    
ax2=plt.subplot2grid((1,1), (0,0))
ax2.axhline(y=0.5, xmin=0, xmax=15, color = 'k',linestyle='--')
plt.ylabel('<J(x).J(x+r)>')
plt.xlabel('log r[Mpc/h]')   
plt.title('%s_%s_%s_%s'%(sim_type,cosmology,snapshot,particles_filt))
plt.legend(loc='upper right')

ax2.plot(results[:,0],results[:,2],'g-',label='spin_spin')
ax2.fill_between(results[:,0], results[:,2]-abs(results[:,4]), results[:,2]+abs(results[:,3]),facecolor='green',alpha=0.3)

plt.savefig('/scratch/GAMNSCM2/halo_halo_plts/%s/%s/halohalodp%s_%s_%s_%s.png'%(sim_type,cosmology,sim_type,cosmology,snapshot,particles_filt))

lss_type=[3,2,1,0]           #Cluster-3 Filament-2 Sheet-1 Void-0
method='bootstrap'   #Not optional for this code
dp_mthd='subdiv'             # 'increm', 'hiho' & 'subdiv'
smooth_scl='na'       #Smoothing scale in physical units Mpc/h. 2  3.5  5

posterior_plt(cosmology,diction_2,results,hist_bins,sim_sz,grid_nodes,smooth_scl,tot_dist_bins,particles_filt,lss_type,method,sim_type,snapshot,den_type,dp_mthd)
