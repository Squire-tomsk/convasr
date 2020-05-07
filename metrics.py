import os
import math
import collections
import json
import functools
import torch
import Levenshtein

placeholder = '|' 
space = ' '
silence = placeholder + space

def align(hyp, ref):
	aligner = Needleman()
	aligner.separator = placeholder
	aligner.score_sub = -2
	aligner.score_del = -4
	aligner.score_ins = -3
	ref, hyp = aligner.align(list(ref), list(hyp))
	return ''.join(hyp), ''.join(ref)

def split_by_space(hyp, ref):
	words = []
	k = None
	for i in range(1 + len(ref)):
		if i == len(ref) or ref[i] == space:
			ref_word, hyp_word = ref[k : i], hyp[k : i]
			if ref_word:
				words.append((hyp_word, ref_word))
			k = i + 1
	return words

def align_words(hyp, ref, break_ref = False):
	hyp, ref = map(list, align(hyp, ref))

	words = split_by_space(hyp, ref)

	if break_ref:
		words_ = []
		for hyp_word, ref_word in words:
			ref_charinds = [i for i, c in enumerate(ref_word) if c != placeholder]
			ref_word, hyp_word = list(ref_word), list(hyp_word)
			for i in range(len(ref_word)):
				if (not ref_charinds or i < ref_charinds[0] or i > ref_charinds[-1]) and hyp_word[i] == space and ref_word[i] == placeholder:
					ref_word[i] = space
			words_.extend(split_by_space(hyp_word, ref_word))

		words = words_

	word_alignment = [dict(hyp = ''.join(hyp), ref = ''.join(ref), type = t) for hyp, ref in words for t, e in [word_alignment_error_type(hyp, ref)]]
	return ''.join(hyp), ''.join(ref), word_alignment

def analyze(ref, hyp, labels, audio_path, phonetic_replace_groups = [], vocab = set(), full = False, break_ref_alignment = True, **kwargs):
	hyp, ref = min((cer(h, r), (h, r)) for r in labels.split_candidates(ref) for h in labels.split_candidates(hyp))[1]
	hyp_postproc, ref_postproc = map(functools.partial(labels.postprocess_transcript, collapse_repeat = True), [hyp, ref])
	hyp_phonetic, ref_phonetic = map(functools.partial(labels.postprocess_transcript, phonetic_replace_groups = phonetic_replace_groups), [hyp_postproc, ref_postproc])
	
	a = dict(labels_name = labels.name, labels = str(labels), audio_path = audio_path, audio_name = os.path.basename(audio_path), hyp_postrpoc = hyp_postproc, ref_postproc = ref_postproc, ref = ref, hyp = hyp, cer = cer(hyp_postproc, ref_postproc), wer = wer(hyp_postproc, ref_postproc), per = cer(hyp_phonetic, ref_phonetic), phonetic = dict(ref = ref_phonetic, hyp = hyp_phonetic), der = sum(w in vocab for w in hyp.split()) / (1 + hyp.count(' ')), **kwargs)
	
	if full:
		hyp, ref, word_alignment = align_words(hyp, ref, break_ref = break_ref_alignment)
		phonetic_group = lambda c: ([i for i, g in enumerate(phonetic_replace_groups) if c in g] + [c])[0]
		hypref_pseudo = {t : (' '.join((r_ if word_alignment_error_type(h_, r_)[0] in dict(typo_easy = ['typo_easy'], typo_hard = ['typo_easy', 'typo_hard'], missing = ['missing'], missing_ref = ['missing_ref'])[t] else h_).replace(placeholder, '') for w in word_alignment for r_, h_ in [(w['ref'], w['hyp'])] ), ref.replace(placeholder, '')) for t in error_types}

		errors = {t : [dict(hyp = r['hyp'], ref = r['ref']) for r in word_alignment if r['type'] == t] for t in error_types}
	
		a.update(dict(
			alignment = dict(ref = ref, hyp = hyp),
			words = word_alignment,
			error_stats = dict(
				spaces = dict(
					delete = sum(ref[i] == space and hyp[i] != space for i in range(len(ref))),
					insert = sum(hyp[i] == space and ref[i] != space for i in range(len(ref))),
					total =  sum(ref[i] == space for i in range(len(ref)))
				),
				chars = dict(
					ok = sum(ref[i] == hyp[i] for i in range(len(ref))), 
					replace = sum(ref[i] != placeholder and ref[i] != hyp[i] and hyp[i] != placeholder for i in range(len(ref))),
					replace_phonetic = sum(ref[i] != placeholder and ref[i] != hyp[i] and hyp[i] != placeholder and phonetic_group(ref[i]) == phonetic_group(hyp[i]) for i in range(len(ref))), 
					delete = sum(ref[i] != placeholder and ref[i] != hyp[i] and hyp[i] == placeholder for i in range(len(ref))),
					insert = sum(ref[i] == placeholder and hyp[i] != placeholder for i in range(len(ref))),
					total = len(ref)
				),
				words = dict(
					missing_prefix = sum(w['hyp'][0] in silence for w in word_alignment),
					missing_suffix = sum(w['hyp'][-1] in silence for w in word_alignment),
					ok_prefix_suffix = sum(w['hyp'][0] not in silence and w['hyp'][-1] not in silence for w in word_alignment),
					delete = sum(w['hyp'].count('|') > len(w['ref']) // 2 for w in word_alignment),
					total = len(word_alignment),
					errors = errors,
				),
			),
			mer = len(errors['missing']) / len(word_alignment),
			cer_easy = cer(*hypref_pseudo['typo_easy']),
			cer_hard = cer(*hypref_pseudo['typo_hard']),
			cer_missing = cer(*hypref_pseudo['missing'])
		))

	return a

def nanmean(dictlist, key):
	return float(torch.FloatTensor([r[key] for r in dictlist if key in r and not math.isinf(r[key]) and not math.isnan(r[key])] or [-1.0]).mean())

def aggregate(analyzed, p = 0.5):
	stats = dict(
		loss_avg = nanmean(analyzed, 'loss'),
		entropy_avg = nanmean(analyzed, 'entropy'),
		cer_avg = nanmean(analyzed, 'cer'),
		wer_avg = nanmean(analyzed, 'wer'),
		mer_avg = nanmean(analyzed, 'mer'),
		cer_easy_avg = nanmean(analyzed, 'cer_easy'),
		cer_hard_avg = nanmean(analyzed, 'cer_hard'),
		cer_missing_avg = nanmean(analyzed, 'cer_missing'),
		der_avg = nanmean(analyzed, 'der')
	)

	errs = collections.defaultdict(int)
	errs_words = {t : [] for t in error_types}
	for a in analyzed:
		if 'words' in a: 
			for hyp, ref in map(lambda b: (b['hyp'], b['ref']), sum(a['error_stats']['words']['errors'].values(), [])):
				t, e = word_alignment_error_type(hyp, ref)
				e = e if t == 'typo_easy' else -1 if t == 'typo_hard' else -2
				errs[e] += 1
				errs_words[t].append(dict(ref = ref, hyp = hyp))
	stats['errors_distribution'] = dict(collections.OrderedDict(sorted(errs.items())))
	stats.update(errs_words)
			
	return stats

def word_alignment_error_type(hyp, ref, p = 0.5, E = 3, L = 4, placeholder = '|'):
	e = sum(ch != cr for ch, cr in zip(hyp, ref))
	ref_placeholders = ref.count(placeholder)
	ref_chars = len(ref) - ref_placeholders
	is_typo = e > 0 and ((hyp.count(placeholder) < p * len(ref) and ref_placeholders < p * len(ref)))
	
	if hyp == ref:
		return 'ok', e
	elif is_typo:
		easy = e <= E and ref_chars >= L
		return 'typo_' + ('easy' if easy else 'hard'), e
	else:
		source = '_ref' if len(ref) > 3 and ref_placeholders >= p * len(ref) else ''
		return 'missing' + source, e

error_types = ['typo_easy', 'typo_hard', 'missing', 'missing_ref']

def quantiles(tensor):
	tensor = tensor.sort().values
	return {k : '{:.2f}'.format(float(tensor[int(len(tensor) * k / 100)])) for k in range(0, 100, 10)}

def cer(hyp, ref, edit_distance = Levenshtein.distance):
	cer_ref_len = len(ref.replace(' ', '')) or 1
	return edit_distance(hyp.replace(' ', '').lower(), ref.replace(' ', '').lower()) / cer_ref_len if hyp != ref else 0

def wer(hyp, ref, edit_distance = Levenshtein.distance):
	# build mapping of words to integers, Levenshtein package only accepts strings
	b = set(hyp.split() + ref.split())
	word2char = dict(zip(b, range(len(b))))
	wer_ref_len = len(ref.split()) or 1
	return edit_distance(''.join([chr(word2char[w]) for w in hyp.split()]), ''.join([chr(word2char[w]) for w in ref.split()])) / wer_ref_len if hyp != ref else 0

def levenshtein(a, b):
	"""Calculates the Levenshtein distance between a and b.
	The code was copied from: http://hetland.org/coding/python/levenshtein.py
	"""
	n, m = len(a), len(b)
	if n > m:
		# Make sure n <= m, to use O(min(n,m)) space
		a, b = b, a
		n, m = m, n

	current = list(range(n + 1))
	for i in range(1, m + 1):
		previous, current = current, [i] + [0] * n
		for j in range(1, n + 1):
			add, delete = previous[j] + 1, current[j - 1] + 1
			change = previous[j - 1]
			if a[j - 1] != b[i - 1]:
				change = change + 1
			current[j] = min(add, delete, change)

	return current[n]

class Needleman:
	# taken from https://github.com/leebird/alignment/blob/master/alignment/alignment.py
	SCORE_UNIFORM = 1
	SCORE_PROPORTION = 2

	def __init__(self):
		self.seq_a = None
		self.seq_b = None
		self.len_a = None
		self.len_b = None
		self.score_null = 5
		self.score_sub = -100
		self.score_del = -3
		self.score_ins = -3
		self.separator = '|'
		self.mode = self.SCORE_UNIFORM
		self.semi_global = False
		self.matrix = None

	def set_score(self, score_null=None, score_sub=None, score_del=None, score_ins=None):
		if score_null is not None:
			self.score_null = score_null
		if score_sub is not None:
			self.score_sub = score_sub
		if score_del is not None:
			self.score_del = score_del
		if score_ins is not None:
			self.score_ins = score_ins

	def match(self, a, b):
		if a == b and self.mode == self.SCORE_UNIFORM:
			return self.score_null
		elif self.mode == self.SCORE_UNIFORM:
			return self.score_sub
		elif a == b:
			return self.score_null * len(a)
		else:
			return self.score_sub * len(a)

	def delete(self, a):
		"""
		deleted elements are on seqa
		"""
		if self.mode == self.SCORE_UNIFORM:
			return self.score_del
		return self.score_del * len(a)

	def insert(self, a):
		"""
		inserted elements are on seqb
		"""
		if self.mode == self.SCORE_UNIFORM:
			return self.score_ins
		return self.score_ins * len(a)

	def score(self, aligned_seq_a, aligned_seq_b):
		score = 0
		for a, b in zip(aligned_seq_a, aligned_seq_b):
			if a == b:
				score += self.score_null
			else:
				if a == self.separator:
					score += self.score_ins
				elif b == self.separator:
					score += self.score_del
				else:
					score += self.score_sub
		return score

	def map_alignment(self, aligned_seq_a, aligned_seq_b):
		map_b2a = []
		idx = 0
		for x, y in zip(aligned_seq_a, aligned_seq_b):
			if x == y:
				# if two positions are the same
				map_b2a.append(idx)
				idx += 1
			elif x == self.separator:
				# if a character is inserted in b, map b's
				# position to previous index in a
				# b[0]=0, b[1]=1, b[2]=1, b[3]=2
				# aa|bbb
				# aaabbb
				map_b2a.append(idx)
			elif y == self.separator:
				# if a character is deleted in a, increase
				# index in a, skip this position
				# b[0]=0, b[1]=1, b[2]=3
				# aaabbb
				# aa|bbb
				idx += 1
				continue
		return map_b2a

	def init_matrix(self):
		rows = self.len_a + 1
		cols = self.len_b + 1
		self.matrix = [[0] * cols for i in range(rows)]

	def compute_matrix(self):
		seq_a = self.seq_a
		seq_b = self.seq_b
		len_a = self.len_a
		len_b = self.len_b

		if not self.semi_global:
			for i in range(1, len_a + 1):
				self.matrix[i][0] = self.delete(seq_a[i - 1]) + self.matrix[i - 1][0]
			for i in range(1, len_b + 1):
				self.matrix[0][i] = self.insert(seq_b[i - 1]) + self.matrix[0][i - 1]

		for i in range(1, len_a + 1):
			for j in range(1, len_b + 1):
				"""
				Note that rows = len_a+1, cols = len_b+1
				"""

				score_sub = self.matrix[i - 1][j - 1] + self.match(seq_a[i - 1], seq_b[j - 1])
				score_del = self.matrix[i - 1][j] + self.delete(seq_a[i - 1])
				score_ins = self.matrix[i][j - 1] + self.insert(seq_b[j - 1])
				self.matrix[i][j] = max(score_sub, score_del, score_ins)

	def backtrack(self):
		aligned_seq_a, aligned_seq_b = [], []
		seq_a, seq_b = self.seq_a, self.seq_b

		if self.semi_global:
			# semi-global settings, len_a = row numbers, column length, len_b = column number, row length
			last_col_max, val = max(enumerate([row[-1] for row in self.matrix]), key=lambda a: a[1])
			last_row_max, val = max(enumerate([col for col in self.matrix[-1]]), key=lambda a: a[1])

			if self.len_a < self.len_b:
				i, j = self.len_a, last_row_max
				aligned_seq_a = [self.separator] * (self.len_b - last_row_max)
				aligned_seq_b = seq_b[last_row_max:]
			else:
				i, j = last_col_max, self.len_b
				aligned_seq_a = seq_a[last_col_max:]
				aligned_seq_b = [self.separator] * (self.len_a - last_col_max)
		else:
			i, j = self.len_a, self.len_b

		mat = self.matrix

		while i > 0 or j > 0:
			# from end to start, choose insert/delete over match for a tie
			# why?
			if self.semi_global and (i == 0 or j == 0):
				if i == 0 and j > 0:
					aligned_seq_a = [self.separator] * j + aligned_seq_a
					aligned_seq_b = seq_b[:j] + aligned_seq_b
				elif i > 0 and j == 0:
					aligned_seq_a = seq_a[:i] + aligned_seq_a
					aligned_seq_b = [self.separator] * i + aligned_seq_b
				break

			if j > 0 and mat[i][j] == mat[i][j - 1] + self.insert(seq_b[j - 1]):
				aligned_seq_a.insert(0, self.separator * len(seq_b[j - 1]))
				aligned_seq_b.insert(0, seq_b[j - 1])
				j -= 1

			elif i > 0 and mat[i][j] == mat[i - 1][j] + self.delete(seq_a[i - 1]):
				aligned_seq_a.insert(0, seq_a[i - 1])
				aligned_seq_b.insert(0, self.separator * len(seq_a[i - 1]))
				i -= 1

			elif i > 0 and j > 0 and mat[i][j] == mat[i - 1][j - 1] + self.match(seq_a[i - 1], seq_b[j - 1]):
				aligned_seq_a.insert(0, seq_a[i - 1])
				aligned_seq_b.insert(0, seq_b[j - 1])
				i -= 1
				j -= 1

			else:
				print(seq_a)
				print(seq_b)
				print(aligned_seq_a)
				print(aligned_seq_b)
				# print(mat)
				raise Exception('backtrack error', i, j, seq_a[i - 2:i + 1], seq_b[j - 2:j + 1])
				pass

		return aligned_seq_a, aligned_seq_b

	def align(self, seq_a, seq_b, semi_global=True, mode=None):
		self.seq_a = seq_a
		self.seq_b = seq_b
		self.len_a = len(self.seq_a)
		self.len_b = len(self.seq_b)

		self.semi_global = semi_global

		# 0: left-end 0-penalty, 1: right-end 0-penalty, 2: both ends 0-penalty
		# self.semi_end = semi_end

		if mode is not None:
			self.mode = mode
		self.init_matrix()
		self.compute_matrix()
		return self.backtrack()

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers()
	
	cmd = subparsers.add_parser('analyze')
	cmd.add_argument('--hyp', required = True)
	cmd.add_argument('--ref', required = True)
	cmd.set_defaults(func = analyze)

	cmd = subparsers.add_parser('align')
	cmd.add_argument('--hyp', required = True)
	cmd.add_argument('--ref', required = True)
	cmd.set_defaults(func = lambda hyp, ref: print('\n'.join(f'{k}: {v}' for k, v in zip(['hyp', 'ref'], align(hyp, ref)))))

	args = parser.parse_args()
	args = vars(parser.parse_args())
	func = args.pop('func')
	func(**args)
