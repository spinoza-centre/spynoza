

#---------------------------------
# New invocation of recon-all ma  1 mei 2017 17:40:40 CEST 

 mri_convert /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/sub-0020/anat/sub-0020_T1w.nii.gz /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/orig/001.mgz 



#---------------------------------
# New invocation of recon-all ma  1 mei 2017 17:41:03 CEST 
#--------------------------------------------
#@# MotionCor ma  1 mei 2017 17:41:03 CEST

 cp /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/orig/001.mgz /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/rawavg.mgz 


 mri_convert /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/rawavg.mgz /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/orig.mgz --conform 


 mri_add_xform_to_header -c /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/transforms/talairach.xfm /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/orig.mgz /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/orig.mgz 

#--------------------------------------------
#@# Talairach ma  1 mei 2017 17:41:10 CEST

 mri_nu_correct.mni --no-rescale --i orig.mgz --o orig_nu.mgz --n 1 --proto-iters 1000 --distance 50 


 talairach_avi --i orig_nu.mgz --xfm transforms/talairach.auto.xfm 

talairach_avi log file is transforms/talairach_avi.log...

 cp transforms/talairach.auto.xfm transforms/talairach.xfm 

#--------------------------------------------
#@# Talairach Failure Detection ma  1 mei 2017 17:42:24 CEST

 talairach_afd -T 0.005 -xfm transforms/talairach.xfm 


 awk -f /usr/local/freesurfer/bin/extract_talairach_avi_QA.awk /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/transforms/talairach_avi.log 


 tal_QC_AZS /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/transforms/talairach_avi.log 

#--------------------------------------------
#@# Nu Intensity Correction ma  1 mei 2017 17:42:24 CEST

 mri_nu_correct.mni --i orig.mgz --o nu.mgz --uchar transforms/talairach.xfm --n 2 


 mri_add_xform_to_header -c /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/transforms/talairach.xfm nu.mgz nu.mgz 

#--------------------------------------------
#@# Intensity Normalization ma  1 mei 2017 17:43:40 CEST

 mri_normalize -g 1 -mprage nu.mgz T1.mgz 

#--------------------------------------------
#@# Skull Stripping ma  1 mei 2017 17:45:13 CEST

 mri_em_register -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mri_em_register.skull.dat -skull nu.mgz /usr/local/freesurfer/average/RB_all_withskull_2016-05-10.vc700.gca transforms/talairach_with_skull.lta 


 mri_watershed -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mri_watershed.dat -T1 -brain_atlas /usr/local/freesurfer/average/RB_all_withskull_2016-05-10.vc700.gca transforms/talairach_with_skull.lta T1.mgz brainmask.auto.mgz 


 cp brainmask.auto.mgz brainmask.mgz 

#-------------------------------------
#@# EM Registration ma  1 mei 2017 17:57:22 CEST

 mri_em_register -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mri_em_register.dat -uns 3 -mask brainmask.mgz nu.mgz /usr/local/freesurfer/average/RB_all_2016-05-10.vc700.gca transforms/talairach.lta 

#--------------------------------------
#@# CA Normalize ma  1 mei 2017 18:07:17 CEST

 mri_ca_normalize -c ctrl_pts.mgz -mask brainmask.mgz nu.mgz /usr/local/freesurfer/average/RB_all_2016-05-10.vc700.gca transforms/talairach.lta norm.mgz 

#--------------------------------------
#@# CA Reg ma  1 mei 2017 18:08:20 CEST

 mri_ca_register -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mri_ca_register.dat -nobigventricles -T transforms/talairach.lta -align-after -mask brainmask.mgz norm.mgz /usr/local/freesurfer/average/RB_all_2016-05-10.vc700.gca transforms/talairach.m3z 

