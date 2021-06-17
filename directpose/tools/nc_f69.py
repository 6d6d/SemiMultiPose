# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
r"""
Basic training script for PyTorch
"""

# Set up custom environment before nearly anything else is imported
# NOTE: this should be the first import (no not reorder)
from maskrcnn_benchmark.utils.env import setup_environment  # noqa F401 isort:skip

import argparse
import os
import sys
import pdb

import torch
from maskrcnn_benchmark.config import cfg
from maskrcnn_benchmark.data import make_data_loader
from maskrcnn_benchmark.solver import make_lr_scheduler
from maskrcnn_benchmark.solver import make_optimizer
from maskrcnn_benchmark.engine.inference import inference
from maskrcnn_benchmark.engine.trainer import do_train
from maskrcnn_benchmark.modeling.detector import build_detection_model
from maskrcnn_benchmark.utils.checkpoint import DetectronCheckpointer
from maskrcnn_benchmark.utils.collect_env import collect_env_info
from maskrcnn_benchmark.utils.comm import synchronize, get_rank
from maskrcnn_benchmark.utils.imports import import_file
from maskrcnn_benchmark.utils.logger import setup_logger
from maskrcnn_benchmark.utils.miscellaneous import mkdir


def is_pytorch_1_1_0_or_later():
    return [int(_) for _ in torch.__version__.split(".")[:3]] >= [1, 1, 0]


def train(cfg, local_rank, distributed, loss_type,alpha,beta,version):
#     assert is_pytorch_1_1_0_or_later()
    model = build_detection_model(cfg)
    device = torch.device(cfg.MODEL.DEVICE)
    model.to(device)

    if distributed:
        model = torch.nn.SyncBatchNorm.convert_sync_batchnorm(model)

    optimizer = make_optimizer(cfg, model)
    scheduler = make_lr_scheduler(cfg, optimizer)

    if distributed:
        model = torch.nn.parallel.DistributedDataParallel(
            model, device_ids=[local_rank], output_device=local_rank,
            # this should be removed if we update BatchNorm stats
            broadcast_buffers=False,
        )

    arguments = {}
    arguments["iteration"] = 0

    output_dir = cfg.OUTPUT_DIR

    save_to_disk = get_rank() == 0
    checkpointer = DetectronCheckpointer(
        cfg, model, optimizer, scheduler, output_dir, save_to_disk
    )
    
    extra_checkpoint_data = checkpointer.load(cfg.MODEL.WEIGHT)
    arguments.update(extra_checkpoint_data)

    data_loader = make_data_loader(
        cfg,
        is_train=True,
        is_distributed=distributed,
        start_iter=arguments["iteration"],
        use_25 = True
    )

    checkpoint_period = cfg.SOLVER.CHECKPOINT_PERIOD

    do_train(
        model,
        data_loader,
        optimizer,
        scheduler,
        checkpointer,
        device,
        checkpoint_period,
        arguments,
        loss_type,
        alpha=alpha,
        beta=beta,
        version=version+"fbf5re"
    )

    return model


def run_test(cfg, model, distributed):
    if distributed:
        model = model.module
    torch.cuda.empty_cache()  # TODO check if it helps
    iou_types = ("bbox",)
    if cfg.MODEL.MASK_ON:
        iou_types = iou_types + ("segm",)
    if cfg.MODEL.KEYPOINT_ON:
        iou_types = iou_types + ("keypoints",)
    output_folders = [None] * len(cfg.DATASETS.TEST)
    dataset_names = cfg.DATASETS.TEST
    if cfg.OUTPUT_DIR:
        for idx, dataset_name in enumerate(dataset_names):
            output_folder = os.path.join(cfg.OUTPUT_DIR, "inference", dataset_name)
            mkdir(output_folder)
            output_folders[idx] = output_folder
    data_loaders_val = make_data_loader(cfg, is_train=False, is_distributed=distributed)
    for output_folder, dataset_name, data_loader_val in zip(output_folders, dataset_names, data_loaders_val):
        inference(
            model,
            data_loader_val,
            dataset_name=dataset_name,
            iou_types=iou_types,
            box_only=False if cfg.MODEL.FCOS_ON or cfg.MODEL.RETINANET_ON else cfg.MODEL.RPN_ONLY,
            device=cfg.MODEL.DEVICE,
            expected_results=cfg.TEST.EXPECTED_RESULTS,
            expected_results_sigma_tol=cfg.TEST.EXPECTED_RESULTS_SIGMA_TOL,
            output_folder=output_folder,
        )
        synchronize()

print("before")
print(str(sys.argv[0]))
print(str(sys.argv[1]))
loss_type = str(sys.argv[1])
number_data = str(sys.argv[2])
version = str(sys.argv[3])
alpha = str(sys.argv[4])
#beta = str(sys.argv[5])
print("alpha", alpha, number_data)
print("after")
#pdb.set_trace()
train_data = 'bee_' + number_data +'_train_cocostyle'
num_gpus = 1#int(os.environ["WORLD_SIZE"]) if "WORLD_SIZE" in os.environ else 1
distributed = num_gpus > 1
local_rank = 0

if distributed:
    torch.cuda.set_device(local_rank)
    torch.distributed.init_process_group(
        backend="nccl", init_method="env://"
    )
    synchronize()

    
    
#weight_p = 'training_dir/250/standard_small_im_lr/0/fcos_kps_ms_training_R_50_FPN_1x_bee/model_0007500.pth'
if loss_type == "standard":
    weight_p = 'training_dir/25/redo/standard_res_f5f.001_'+str(alpha)+'/'+version + '/fcos_kps_ms_training_R_50_FPN_1x_bee/model_0003000.pth'
    print(weight_p)
    original = torch.load(weight_p)
    new_m = {"model": original["model"]}
    torch.save(new_m, 'training_dir/250/f5'+ alpha + version+ '_model_0500.pth')
else:
    weight_p = 'training_dir/25/redo/combined_res_f5f.001_'+str(alpha)+'/'+version + '/fcos_kps_ms_training_R_50_FPN_1x_bee/model_0003000.pth'
    original = torch.load(weight_p)
    new_m = {"model": original["model"]}
    torch.save(new_m, 'training_dir/250/f5'+ alpha + version+ '_model_0500.pth')
    
config_file = "/home/bsb2144/directpose/configs/fcos/fcos_kps_ms_training_R_50_FPN_1x.yaml"
cfg.merge_from_file(config_file)
cfg.merge_from_list(['DATALOADER.NUM_WORKERS', 2, \
                     'DATATYPE', 'bee', \
        'OUTPUT_DIR', 'training_dir/' + number_data + '/redo/' + loss_type + '_res_f69f.0001_' + alpha+'/' + version +'/fcos_kps_ms_training_R_50_FPN_1x_bee', \
        'SOLVER.KPS_GRAD_MULT', 10.0, \
        'SOLVER.MAX_GRAD_NORM', 5.0, \
        'SOLVER.POWER', 1.0, \
        'INPUT.CROP_SIZE', 800, \
        'INPUT.MIN_SIZE_RANGE_TRAIN', '(480, 1600)', \
        'INPUT.MAX_SIZE_TRAIN', 2666, \
        'MODEL.WEIGHT', 'training_dir/250/f5'+ alpha + version+ '_model_0500.pth', \
        'MODEL.RPN.BATCH_SIZE_PER_IMAGE', 1,\
        'MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE', 1,\
        'SOLVER.IMS_PER_BATCH', 3, \
        'SOLVER.MAX_ITER', 180000, \
        'SOLVER.WARMUP_ITERS', 0, \
        'SOLVER.BASE_LR', .001, \
        'SOLVER.WEIGHT_DECAY', 0.00000000000001, \
        'MODEL.HEATMAPS_LOSS_WEIGHT', 4.0, \
        'DATASETS.TRAIN', "('bee_train_cocostyle_small', 'bee_train_cocostyle_small')"
        ])

#  
output_dir = cfg.OUTPUT_DIR
if output_dir:
    mkdir(output_dir)

logger = setup_logger("maskrcnn_benchmark", output_dir, get_rank())
logger.info("Using {} GPUs".format(num_gpus))
logger.info(cfg)

logger.info("Collecting env info (might take some time)")
logger.info("\n" + collect_env_info())

logger.info("Loaded configuration file {}".format(config_file))
with open(config_file, "r") as cf:
    config_str = "\n" + cf.read()
    logger.info(config_str)
logger.info("Running with config:\n{}".format(cfg))

beta = 0

model = train(cfg, local_rank, distributed, loss_type,alpha,beta,version)