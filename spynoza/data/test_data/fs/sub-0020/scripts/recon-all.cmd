

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

#--------------------------------------
#@# SubCort Seg ma  1 mei 2017 19:36:51 CEST

 mri_ca_label -relabel_unlikely 9 .3 -prior 0.5 -align norm.mgz transforms/talairach.m3z /usr/local/freesurfer/average/RB_all_2016-05-10.vc700.gca aseg.auto_noCCseg.mgz 


 mri_cc -aseg aseg.auto_noCCseg.mgz -o aseg.auto.mgz -lta /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/mri/transforms/cc_up.lta sub-0020 

#--------------------------------------
#@# Merge ASeg ma  1 mei 2017 20:10:22 CEST

 cp aseg.auto.mgz aseg.presurf.mgz 

#--------------------------------------------
#@# Intensity Normalization2 ma  1 mei 2017 20:10:22 CEST

 mri_normalize -mprage -aseg aseg.presurf.mgz -mask brainmask.mgz norm.mgz brain.mgz 

#--------------------------------------------
#@# Mask BFS ma  1 mei 2017 20:12:35 CEST

 mri_mask -T 5 brain.mgz brainmask.mgz brain.finalsurfs.mgz 

#--------------------------------------------
#@# WM Segmentation ma  1 mei 2017 20:12:36 CEST

 mri_segment -mprage brain.mgz wm.seg.mgz 


 mri_edit_wm_with_aseg -keep-in wm.seg.mgz brain.mgz aseg.presurf.mgz wm.asegedit.mgz 


 mri_pretess wm.asegedit.mgz wm norm.mgz wm.mgz 

#--------------------------------------------
#@# Fill ma  1 mei 2017 20:13:53 CEST

 mri_fill -a ../scripts/ponscc.cut.log -xform transforms/talairach.lta -segmentation aseg.auto_noCCseg.mgz wm.mgz filled.mgz 

#--------------------------------------------
#@# Tessellate lh ma  1 mei 2017 20:14:19 CEST

 mri_pretess ../mri/filled.mgz 255 ../mri/norm.mgz ../mri/filled-pretess255.mgz 


 mri_tessellate ../mri/filled-pretess255.mgz 255 ../surf/lh.orig.nofix 


 rm -f ../mri/filled-pretess255.mgz 


 mris_extract_main_component ../surf/lh.orig.nofix ../surf/lh.orig.nofix 

#--------------------------------------------
#@# Tessellate rh ma  1 mei 2017 20:14:23 CEST

 mri_pretess ../mri/filled.mgz 127 ../mri/norm.mgz ../mri/filled-pretess127.mgz 


 mri_tessellate ../mri/filled-pretess127.mgz 127 ../surf/rh.orig.nofix 


 rm -f ../mri/filled-pretess127.mgz 


 mris_extract_main_component ../surf/rh.orig.nofix ../surf/rh.orig.nofix 

#--------------------------------------------
#@# Smooth1 lh ma  1 mei 2017 20:14:27 CEST

 mris_smooth -nw -seed 1234 ../surf/lh.orig.nofix ../surf/lh.smoothwm.nofix 

#--------------------------------------------
#@# Smooth1 rh ma  1 mei 2017 20:14:31 CEST

 mris_smooth -nw -seed 1234 ../surf/rh.orig.nofix ../surf/rh.smoothwm.nofix 

#--------------------------------------------
#@# Inflation1 lh ma  1 mei 2017 20:14:34 CEST

 mris_inflate -no-save-sulc ../surf/lh.smoothwm.nofix ../surf/lh.inflated.nofix 

#--------------------------------------------
#@# Inflation1 rh ma  1 mei 2017 20:14:59 CEST

 mris_inflate -no-save-sulc ../surf/rh.smoothwm.nofix ../surf/rh.inflated.nofix 

#--------------------------------------------
#@# QSphere lh ma  1 mei 2017 20:15:24 CEST

 mris_sphere -q -seed 1234 ../surf/lh.inflated.nofix ../surf/lh.qsphere.nofix 

#--------------------------------------------
#@# QSphere rh ma  1 mei 2017 20:17:59 CEST

 mris_sphere -q -seed 1234 ../surf/rh.inflated.nofix ../surf/rh.qsphere.nofix 

#--------------------------------------------
#@# Fix Topology Copy lh ma  1 mei 2017 20:20:48 CEST

 cp ../surf/lh.orig.nofix ../surf/lh.orig 


 cp ../surf/lh.inflated.nofix ../surf/lh.inflated 

#--------------------------------------------
#@# Fix Topology Copy rh ma  1 mei 2017 20:20:48 CEST

 cp ../surf/rh.orig.nofix ../surf/rh.orig 


 cp ../surf/rh.inflated.nofix ../surf/rh.inflated 

#@# Fix Topology lh ma  1 mei 2017 20:20:48 CEST

 mris_fix_topology -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_fix_topology.lh.dat -mgz -sphere qsphere.nofix -ga -seed 1234 sub-0020 lh 

#@# Fix Topology rh ma  1 mei 2017 20:27:40 CEST

 mris_fix_topology -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_fix_topology.rh.dat -mgz -sphere qsphere.nofix -ga -seed 1234 sub-0020 rh 


 mris_euler_number ../surf/lh.orig 


 mris_euler_number ../surf/rh.orig 


 mris_remove_intersection ../surf/lh.orig ../surf/lh.orig 


 rm ../surf/lh.inflated 


 mris_remove_intersection ../surf/rh.orig ../surf/rh.orig 


 rm ../surf/rh.inflated 

#--------------------------------------------
#@# Make White Surf lh ma  1 mei 2017 20:32:13 CEST

 mris_make_surfaces -aseg ../mri/aseg.presurf -white white.preaparc -noaparc -whiteonly -mgz -T1 brain.finalsurfs sub-0020 lh 

#--------------------------------------------
#@# Make White Surf rh ma  1 mei 2017 20:35:41 CEST

 mris_make_surfaces -aseg ../mri/aseg.presurf -white white.preaparc -noaparc -whiteonly -mgz -T1 brain.finalsurfs sub-0020 rh 

#--------------------------------------------
#@# Smooth2 lh ma  1 mei 2017 20:39:12 CEST

 mris_smooth -n 3 -nw -seed 1234 ../surf/lh.white.preaparc ../surf/lh.smoothwm 

#--------------------------------------------
#@# Smooth2 rh ma  1 mei 2017 20:39:16 CEST

 mris_smooth -n 3 -nw -seed 1234 ../surf/rh.white.preaparc ../surf/rh.smoothwm 

#--------------------------------------------
#@# Inflation2 lh ma  1 mei 2017 20:39:19 CEST

 mris_inflate -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_inflate.lh.dat ../surf/lh.smoothwm ../surf/lh.inflated 

#--------------------------------------------
#@# Inflation2 rh ma  1 mei 2017 20:39:43 CEST

 mris_inflate -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_inflate.rh.dat ../surf/rh.smoothwm ../surf/rh.inflated 

#--------------------------------------------
#@# Curv .H and .K lh ma  1 mei 2017 20:40:08 CEST

 mris_curvature -w lh.white.preaparc 


 mris_curvature -thresh .999 -n -a 5 -w -distances 10 10 lh.inflated 

#--------------------------------------------
#@# Curv .H and .K rh ma  1 mei 2017 20:40:57 CEST

 mris_curvature -w rh.white.preaparc 


 mris_curvature -thresh .999 -n -a 5 -w -distances 10 10 rh.inflated 


#-----------------------------------------
#@# Curvature Stats lh ma  1 mei 2017 20:41:47 CEST

 mris_curvature_stats -m --writeCurvatureFiles -G -o ../stats/lh.curv.stats -F smoothwm sub-0020 lh curv sulc 


#-----------------------------------------
#@# Curvature Stats rh ma  1 mei 2017 20:41:49 CEST

 mris_curvature_stats -m --writeCurvatureFiles -G -o ../stats/rh.curv.stats -F smoothwm sub-0020 rh curv sulc 

#--------------------------------------------
#@# Sphere lh ma  1 mei 2017 20:41:52 CEST

 mris_sphere -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_sphere.lh.dat -seed 1234 ../surf/lh.inflated ../surf/lh.sphere 

#--------------------------------------------
#@# Sphere rh ma  1 mei 2017 21:12:30 CEST

 mris_sphere -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_sphere.rh.dat -seed 1234 ../surf/rh.inflated ../surf/rh.sphere 

#--------------------------------------------
#@# Surf Reg lh ma  1 mei 2017 21:37:21 CEST

 mris_register -curv -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_register.lh.dat ../surf/lh.sphere /usr/local/freesurfer/average/lh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif ../surf/lh.sphere.reg 

#--------------------------------------------
#@# Surf Reg rh ma  1 mei 2017 22:11:07 CEST

 mris_register -curv -rusage /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/sub-0020/touch/rusage.mris_register.rh.dat ../surf/rh.sphere /usr/local/freesurfer/average/rh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif ../surf/rh.sphere.reg 

#--------------------------------------------
#@# Jacobian white lh ma  1 mei 2017 22:52:42 CEST

 mris_jacobian ../surf/lh.white.preaparc ../surf/lh.sphere.reg ../surf/lh.jacobian_white 

#--------------------------------------------
#@# Jacobian white rh ma  1 mei 2017 22:52:43 CEST

 mris_jacobian ../surf/rh.white.preaparc ../surf/rh.sphere.reg ../surf/rh.jacobian_white 

#--------------------------------------------
#@# AvgCurv lh ma  1 mei 2017 22:52:45 CEST

 mrisp_paint -a 5 /usr/local/freesurfer/average/lh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif#6 ../surf/lh.sphere.reg ../surf/lh.avg_curv 

#--------------------------------------------
#@# AvgCurv rh ma  1 mei 2017 22:52:46 CEST

 mrisp_paint -a 5 /usr/local/freesurfer/average/rh.folding.atlas.acfb40.noaparc.i12.2016-08-02.tif#6 ../surf/rh.sphere.reg ../surf/rh.avg_curv 

#-----------------------------------------
#@# Cortical Parc lh ma  1 mei 2017 22:52:47 CEST

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub-0020 lh ../surf/lh.sphere.reg /usr/local/freesurfer/average/lh.DKaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.annot 

#-----------------------------------------
#@# Cortical Parc rh ma  1 mei 2017 22:52:56 CEST

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub-0020 rh ../surf/rh.sphere.reg /usr/local/freesurfer/average/rh.DKaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.annot 

#--------------------------------------------
#@# Make Pial Surf lh ma  1 mei 2017 22:53:05 CEST

 mris_make_surfaces -orig_white white.preaparc -orig_pial white.preaparc -aseg ../mri/aseg.presurf -mgz -T1 brain.finalsurfs sub-0020 lh 

#--------------------------------------------
#@# Make Pial Surf rh ma  1 mei 2017 23:02:35 CEST

 mris_make_surfaces -orig_white white.preaparc -orig_pial white.preaparc -aseg ../mri/aseg.presurf -mgz -T1 brain.finalsurfs sub-0020 rh 

#--------------------------------------------
#@# Surf Volume lh ma  1 mei 2017 23:12:35 CEST
#--------------------------------------------
#@# Surf Volume rh ma  1 mei 2017 23:12:37 CEST
#--------------------------------------------
#@# Cortical ribbon mask ma  1 mei 2017 23:12:39 CEST

 mris_volmask --aseg_name aseg.presurf --label_left_white 2 --label_left_ribbon 3 --label_right_white 41 --label_right_ribbon 42 --save_ribbon sub-0020 

#-----------------------------------------
#@# Parcellation Stats lh ma  1 mei 2017 23:20:27 CEST

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.stats -b -a ../label/lh.aparc.annot -c ../label/aparc.annot.ctab sub-0020 lh white 


 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.pial.stats -b -a ../label/lh.aparc.annot -c ../label/aparc.annot.ctab sub-0020 lh pial 

#-----------------------------------------
#@# Parcellation Stats rh ma  1 mei 2017 23:21:14 CEST

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.stats -b -a ../label/rh.aparc.annot -c ../label/aparc.annot.ctab sub-0020 rh white 


 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.pial.stats -b -a ../label/rh.aparc.annot -c ../label/aparc.annot.ctab sub-0020 rh pial 

#-----------------------------------------
#@# Cortical Parc 2 lh ma  1 mei 2017 23:22:01 CEST

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub-0020 lh ../surf/lh.sphere.reg /usr/local/freesurfer/average/lh.CDaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.a2009s.annot 

#-----------------------------------------
#@# Cortical Parc 2 rh ma  1 mei 2017 23:22:14 CEST

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub-0020 rh ../surf/rh.sphere.reg /usr/local/freesurfer/average/rh.CDaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.a2009s.annot 

#-----------------------------------------
#@# Parcellation Stats 2 lh ma  1 mei 2017 23:22:26 CEST

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.a2009s.stats -b -a ../label/lh.aparc.a2009s.annot -c ../label/aparc.annot.a2009s.ctab sub-0020 lh white 

#-----------------------------------------
#@# Parcellation Stats 2 rh ma  1 mei 2017 23:22:50 CEST

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.a2009s.stats -b -a ../label/rh.aparc.a2009s.annot -c ../label/aparc.annot.a2009s.ctab sub-0020 rh white 

#-----------------------------------------
#@# Cortical Parc 3 lh ma  1 mei 2017 23:23:14 CEST

 mris_ca_label -l ../label/lh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub-0020 lh ../surf/lh.sphere.reg /usr/local/freesurfer/average/lh.DKTaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/lh.aparc.DKTatlas.annot 

#-----------------------------------------
#@# Cortical Parc 3 rh ma  1 mei 2017 23:23:23 CEST

 mris_ca_label -l ../label/rh.cortex.label -aseg ../mri/aseg.presurf.mgz -seed 1234 sub-0020 rh ../surf/rh.sphere.reg /usr/local/freesurfer/average/rh.DKTaparc.atlas.acfb40.noaparc.i12.2016-08-02.gcs ../label/rh.aparc.DKTatlas.annot 

#-----------------------------------------
#@# Parcellation Stats 3 lh ma  1 mei 2017 23:23:33 CEST

 mris_anatomical_stats -th3 -mgz -cortex ../label/lh.cortex.label -f ../stats/lh.aparc.DKTatlas.stats -b -a ../label/lh.aparc.DKTatlas.annot -c ../label/aparc.annot.DKTatlas.ctab sub-0020 lh white 

#-----------------------------------------
#@# Parcellation Stats 3 rh ma  1 mei 2017 23:23:56 CEST

 mris_anatomical_stats -th3 -mgz -cortex ../label/rh.cortex.label -f ../stats/rh.aparc.DKTatlas.stats -b -a ../label/rh.aparc.DKTatlas.annot -c ../label/aparc.annot.DKTatlas.ctab sub-0020 rh white 

#-----------------------------------------
#@# WM/GM Contrast lh ma  1 mei 2017 23:24:19 CEST

 pctsurfcon --s sub-0020 --lh-only 

#-----------------------------------------
#@# WM/GM Contrast rh ma  1 mei 2017 23:24:24 CEST

 pctsurfcon --s sub-0020 --rh-only 

#-----------------------------------------
#@# Relabel Hypointensities ma  1 mei 2017 23:24:28 CEST

 mri_relabel_hypointensities aseg.presurf.mgz ../surf aseg.presurf.hypos.mgz 

#-----------------------------------------
#@# AParc-to-ASeg aparc ma  1 mei 2017 23:24:41 CEST

 mri_aparc2aseg --s sub-0020 --volmask --aseg aseg.presurf.hypos --relabel mri/norm.mgz mri/transforms/talairach.m3z /usr/local/freesurfer/average/RB_all_2016-05-10.vc700.gca mri/aseg.auto_noCCseg.label_intensities.txt 

#-----------------------------------------
#@# AParc-to-ASeg a2009s ma  1 mei 2017 23:27:47 CEST

 mri_aparc2aseg --s sub-0020 --volmask --aseg aseg.presurf.hypos --relabel mri/norm.mgz mri/transforms/talairach.m3z /usr/local/freesurfer/average/RB_all_2016-05-10.vc700.gca mri/aseg.auto_noCCseg.label_intensities.txt --a2009s 

#-----------------------------------------
#@# AParc-to-ASeg DKTatlas ma  1 mei 2017 23:30:50 CEST

 mri_aparc2aseg --s sub-0020 --volmask --aseg aseg.presurf.hypos --relabel mri/norm.mgz mri/transforms/talairach.m3z /usr/local/freesurfer/average/RB_all_2016-05-10.vc700.gca mri/aseg.auto_noCCseg.label_intensities.txt --annot aparc.DKTatlas --o mri/aparc.DKTatlas+aseg.mgz 

#-----------------------------------------
#@# APas-to-ASeg ma  1 mei 2017 23:33:54 CEST

 apas2aseg --i aparc+aseg.mgz --o aseg.mgz 

#--------------------------------------------
#@# ASeg Stats ma  1 mei 2017 23:33:58 CEST

 mri_segstats --seg mri/aseg.mgz --sum stats/aseg.stats --pv mri/norm.mgz --empty --brainmask mri/brainmask.mgz --brain-vol-from-seg --excludeid 0 --excl-ctxgmwm --supratent --subcortgray --in mri/norm.mgz --in-intensity-name norm --in-intensity-units MR --etiv --surf-wm-vol --surf-ctx-vol --totalgray --euler --ctab /usr/local/freesurfer/ASegStatsLUT.txt --subject sub-0020 

#-----------------------------------------
#@# WMParc ma  1 mei 2017 23:35:39 CEST

 mri_aparc2aseg --s sub-0020 --labelwm --hypo-as-wm --rip-unknown --volmask --o mri/wmparc.mgz --ctxseg aparc+aseg.mgz 


 mri_segstats --seg mri/wmparc.mgz --sum stats/wmparc.stats --pv mri/norm.mgz --excludeid 0 --brainmask mri/brainmask.mgz --in mri/norm.mgz --in-intensity-name norm --in-intensity-units MR --subject sub-0020 --surf-wm-vol --ctab /usr/local/freesurfer/WMParcStatsLUT.txt --etiv 

INFO: fsaverage subject does not exist in SUBJECTS_DIR
INFO: Creating symlink to fsaverage subject...

 cd /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs; ln -s /usr/local/freesurfer/subjects/fsaverage; cd - 

#--------------------------------------------
#@# BA_exvivo Labels lh ma  1 mei 2017 23:42:14 CEST

 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA1_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA1_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA2_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA2_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA3a_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA3a_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA3b_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA3b_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA4a_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA4a_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA4p_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA4p_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA6_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA6_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA44_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA44_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA45_exvivo.label --trgsubject sub-0020 --trglabel ./lh.BA45_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.V1_exvivo.label --trgsubject sub-0020 --trglabel ./lh.V1_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.V2_exvivo.label --trgsubject sub-0020 --trglabel ./lh.V2_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.MT_exvivo.label --trgsubject sub-0020 --trglabel ./lh.MT_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.entorhinal_exvivo.label --trgsubject sub-0020 --trglabel ./lh.entorhinal_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.perirhinal_exvivo.label --trgsubject sub-0020 --trglabel ./lh.perirhinal_exvivo.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA1_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA1_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA2_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA2_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA3a_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA3a_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA3b_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA3b_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA4a_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA4a_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA4p_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA4p_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA6_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA6_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA44_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA44_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.BA45_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.BA45_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.V1_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.V1_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.V2_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.V2_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.MT_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.MT_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.entorhinal_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.entorhinal_exvivo.thresh.label --hemi lh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/lh.perirhinal_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./lh.perirhinal_exvivo.thresh.label --hemi lh --regmethod surface 


 mris_label2annot --s sub-0020 --hemi lh --ctab /usr/local/freesurfer/average/colortable_BA.txt --l lh.BA1_exvivo.label --l lh.BA2_exvivo.label --l lh.BA3a_exvivo.label --l lh.BA3b_exvivo.label --l lh.BA4a_exvivo.label --l lh.BA4p_exvivo.label --l lh.BA6_exvivo.label --l lh.BA44_exvivo.label --l lh.BA45_exvivo.label --l lh.V1_exvivo.label --l lh.V2_exvivo.label --l lh.MT_exvivo.label --l lh.entorhinal_exvivo.label --l lh.perirhinal_exvivo.label --a BA_exvivo --maxstatwinner --noverbose 


 mris_label2annot --s sub-0020 --hemi lh --ctab /usr/local/freesurfer/average/colortable_BA.txt --l lh.BA1_exvivo.thresh.label --l lh.BA2_exvivo.thresh.label --l lh.BA3a_exvivo.thresh.label --l lh.BA3b_exvivo.thresh.label --l lh.BA4a_exvivo.thresh.label --l lh.BA4p_exvivo.thresh.label --l lh.BA6_exvivo.thresh.label --l lh.BA44_exvivo.thresh.label --l lh.BA45_exvivo.thresh.label --l lh.V1_exvivo.thresh.label --l lh.V2_exvivo.thresh.label --l lh.MT_exvivo.thresh.label --l lh.entorhinal_exvivo.thresh.label --l lh.perirhinal_exvivo.thresh.label --a BA_exvivo.thresh --maxstatwinner --noverbose 


 mris_anatomical_stats -th3 -mgz -f ../stats/lh.BA_exvivo.stats -b -a ./lh.BA_exvivo.annot -c ./BA_exvivo.ctab sub-0020 lh white 


 mris_anatomical_stats -th3 -mgz -f ../stats/lh.BA_exvivo.thresh.stats -b -a ./lh.BA_exvivo.thresh.annot -c ./BA_exvivo.thresh.ctab sub-0020 lh white 

#--------------------------------------------
#@# BA_exvivo Labels rh ma  1 mei 2017 23:45:23 CEST

 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA1_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA1_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA2_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA2_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA3a_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA3a_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA3b_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA3b_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA4a_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA4a_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA4p_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA4p_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA6_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA6_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA44_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA44_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA45_exvivo.label --trgsubject sub-0020 --trglabel ./rh.BA45_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.V1_exvivo.label --trgsubject sub-0020 --trglabel ./rh.V1_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.V2_exvivo.label --trgsubject sub-0020 --trglabel ./rh.V2_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.MT_exvivo.label --trgsubject sub-0020 --trglabel ./rh.MT_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.entorhinal_exvivo.label --trgsubject sub-0020 --trglabel ./rh.entorhinal_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.perirhinal_exvivo.label --trgsubject sub-0020 --trglabel ./rh.perirhinal_exvivo.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA1_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA1_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA2_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA2_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA3a_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA3a_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA3b_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA3b_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA4a_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA4a_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA4p_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA4p_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA6_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA6_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA44_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA44_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.BA45_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.BA45_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.V1_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.V1_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.V2_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.V2_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.MT_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.MT_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.entorhinal_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.entorhinal_exvivo.thresh.label --hemi rh --regmethod surface 


 mri_label2label --srcsubject fsaverage --srclabel /media/lukas/data/Software/Spynoza/spynoza/spynoza/data/test_data/fs/fsaverage/label/rh.perirhinal_exvivo.thresh.label --trgsubject sub-0020 --trglabel ./rh.perirhinal_exvivo.thresh.label --hemi rh --regmethod surface 


 mris_label2annot --s sub-0020 --hemi rh --ctab /usr/local/freesurfer/average/colortable_BA.txt --l rh.BA1_exvivo.label --l rh.BA2_exvivo.label --l rh.BA3a_exvivo.label --l rh.BA3b_exvivo.label --l rh.BA4a_exvivo.label --l rh.BA4p_exvivo.label --l rh.BA6_exvivo.label --l rh.BA44_exvivo.label --l rh.BA45_exvivo.label --l rh.V1_exvivo.label --l rh.V2_exvivo.label --l rh.MT_exvivo.label --l rh.entorhinal_exvivo.label --l rh.perirhinal_exvivo.label --a BA_exvivo --maxstatwinner --noverbose 


 mris_label2annot --s sub-0020 --hemi rh --ctab /usr/local/freesurfer/average/colortable_BA.txt --l rh.BA1_exvivo.thresh.label --l rh.BA2_exvivo.thresh.label --l rh.BA3a_exvivo.thresh.label --l rh.BA3b_exvivo.thresh.label --l rh.BA4a_exvivo.thresh.label --l rh.BA4p_exvivo.thresh.label --l rh.BA6_exvivo.thresh.label --l rh.BA44_exvivo.thresh.label --l rh.BA45_exvivo.thresh.label --l rh.V1_exvivo.thresh.label --l rh.V2_exvivo.thresh.label --l rh.MT_exvivo.thresh.label --l rh.entorhinal_exvivo.thresh.label --l rh.perirhinal_exvivo.thresh.label --a BA_exvivo.thresh --maxstatwinner --noverbose 


 mris_anatomical_stats -th3 -mgz -f ../stats/rh.BA_exvivo.stats -b -a ./rh.BA_exvivo.annot -c ./BA_exvivo.ctab sub-0020 rh white 


 mris_anatomical_stats -th3 -mgz -f ../stats/rh.BA_exvivo.thresh.stats -b -a ./rh.BA_exvivo.thresh.annot -c ./BA_exvivo.thresh.ctab sub-0020 rh white 

