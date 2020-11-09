import math
import torch
import torch.nn.functional as F


@torch.jit.script
def alignment(
	log_probs,
	targets,
	input_lengths,
	target_lengths,
	blank: int = 0,
	pack_backpointers: bool = False,
	finfo_min_fp32: float = torch.finfo(torch.float32).min,
	finfo_min_fp16: float = torch.finfo(torch.float16).min
):
	B = torch.arange(len(targets), device = input_lengths.device)
	_t_a_r_g_e_t_s_ = torch.cat([
		torch.stack([torch.full_like(targets, blank), targets], dim = -1).flatten(start_dim = -2),
		torch.full_like(targets[:, :1], blank)
	],
								dim = -1)
	diff_labels = torch.cat([
		torch.as_tensor([[False, False]], device = targets.device).expand(len(B), -1),
		_t_a_r_g_e_t_s_[:, 2:] != _t_a_r_g_e_t_s_[:, :-2]
	],
							dim = 1)

	zero, zero_padding = torch.tensor(finfo_min_fp16 if log_probs.dtype is torch.float16 else finfo_min_fp32, device = log_probs.device, dtype = log_probs.dtype), 2
	padded_t = zero_padding + _t_a_r_g_e_t_s_.shape[-1]
	log_alpha = torch.full((len(B), padded_t), zero, device = log_probs.device, dtype = log_probs.dtype)
	log_alpha[:, zero_padding + 0] = log_probs[0, :, blank]
	log_alpha[:, zero_padding + 1] = log_probs[0, B, _t_a_r_g_e_t_s_[:, 1]]

	packmask = 0b11
	packnibbles = 4
	padded_t = int(math.ceil(padded_t / packnibbles)) * packnibbles
	backpointers_shape = [len(log_probs), len(B), padded_t]
	backpointers = torch.zeros(
		backpointers_shape if not pack_backpointers else (backpointers_shape[:-1] + (padded_t // packnibbles, )),
		device = log_probs.device,
		dtype = torch.uint8
	)
	backpointer = torch.zeros(backpointers_shape[1:], device = log_probs.device, dtype = torch.uint8)
	packshift = torch.tensor([[[6, 4, 2, 0]]], device = log_probs.device, dtype = torch.uint8)

	for t in range(1, len(log_probs)):
		prev = torch.stack([log_alpha[:, 2:], log_alpha[:, 1:-1], torch.where(diff_labels, log_alpha[:, :-2], zero)])
		log_alpha[:, 2:] = log_probs[t].gather(-1, _t_a_r_g_e_t_s_) + prev.logsumexp(dim = 0)
		backpointer[:, 2:(2 + prev.shape[-1])] = prev.argmax(dim = 0)
		if pack_backpointers:
			torch.sum(backpointer.view(len(backpointer), -1, 4) << packshift, dim = -1, out = backpointers[t])
		else:
			backpointers[t] = backpointer

	l1l2 = log_alpha.gather(
		-1, torch.stack([zero_padding + target_lengths * 2 - 1, zero_padding + target_lengths * 2], dim = -1)
	)

	path = torch.zeros(len(log_probs), len(B), device = log_alpha.device, dtype = torch.long)
	path[input_lengths - 1, B] = zero_padding + target_lengths * 2 - 1 + l1l2.argmax(dim = -1)

	for t in range(len(path) - 1, 0, -1):
		indices = path[t]

		if pack_backpointers:
			backpointer = (backpointers[t].unsqueeze(-1) >> packshift).view_as(backpointer)
		else:
			backpointer = backpointers[t]

		path[t - 1] += indices - backpointer.gather(-1, indices.unsqueeze(-1)).squeeze(-1).bitwise_and_(packmask)
	return torch.zeros_like(_t_a_r_g_e_t_s_, dtype = torch.long).scatter_(
		-1, (path.t() - zero_padding).clamp(min = 0),
		torch.arange(len(path), device = log_alpha.device).expand(len(B), -1)
	)[:, 1::2]
