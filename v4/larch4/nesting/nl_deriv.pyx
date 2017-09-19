

from numpy.math cimport INFINITY
from ..linalg.level1 cimport daxpy_memview
from libc.math cimport pow, exp, log
from scipy.linalg.cython_blas cimport daxpy as _daxpy


cpdef case_dUtility_dFusedParameters(
		int c,

		int n_cases,
		int n_elementals,
		int n_nests,
		int n_edges,

		double[:,:] log_prob_elementals,  # shape = [cases,alts]
		double[:,:] util_elementals,      # shape = [cases,alts]
		double[:,:] util_nests,           # shape = [cases,nests]

		double[:] coef_u_ca,               # shape = (vars_ca)
		double[:,:] coef_u_co,             # shape = (vars_co,alts)
		double[:] coef_q_ca,               # shape = (qvars_ca)
		double[:] coef_mu,                 # shape = (nests)

		double[:,:] d_util_meta,           # shape = (nodes,n_meta_coef)  refs same memory as the d_util_coef_* arrays...
		double[:,:] d_util_coef_u_ca,      # shape = (nodes,vars_ca)
		double[:,:,:] d_util_coef_u_co,    # shape = (nodes,vars_co,alts)
		double[:,:] d_util_coef_q_ca,      # shape = (nodes,qvars_ca)
		double[:,:] d_util_coef_mu,        # shape = (nodes,nests)

		double[:,:,:] data_u_ca,           # shape = (cases,alts,vars_ca)
		double[:,:] data_u_co,             # shape = (cases,vars_co)

		double[:,:] log_conditional_prob,      # shape = (cases,edges)

		int[:] edge_child_slot,            # shape = (edges)
		int[:] edge_parent_slot,           # shape = (edges)
		int[:] first_visit_to_child,       # shape = (edges)
):
	cdef:
		int e, a, nest_slot, dn, up, up_n, n, incx, j
		double cond_prob

	for e in range(n_edges):
		# 'e' is iterated over all the links in the network

		dn = edge_child_slot[e]
		up = edge_parent_slot[e]
		up_n = up - n_elementals

		if log_conditional_prob[c,e] < -1.797e+308: # i.e. -INF
			continue

		# First, we calculate the effect of various parameters on the utility
		# of 'a' directly. For elemental alternatives, this means beta parameters.
		# For other nodes, only mu has a direct effect

		# BETA for SELF (elemental alternatives)
		if dn < n_elementals and first_visit_to_child[e]>0:
			d_util_coef_u_ca[dn,:] = data_u_ca[c,dn,:]
			d_util_coef_u_co[dn,:,dn] = data_u_co[c,:]

		# MU for SELF (adjust the kiddies contributions)
		if dn >= n_elementals and first_visit_to_child[e]>0:
			d_util_coef_mu[dn,dn-n_elementals] += util_nests[c,dn-n_elementals]
			d_util_coef_mu[dn,dn-n_elementals] /= coef_mu[dn-n_elementals]

		# MU for Parent (non-competitive edge)
		cond_prob = exp(log_conditional_prob[c,e])
		if dn < n_elementals:
			d_util_coef_mu[up, up_n] -= cond_prob * util_elementals[c,dn]
		else:
			d_util_coef_mu[up, up_n] -= cond_prob * util_nests[c,dn-n_elementals]

		# Finally, roll up secondary effects on parents
		if cond_prob>0:
			# daxpy_memview(cond_prob,d_util_meta[dn,:],d_util_meta[up,:])
			# # n = d_util_meta.shape[1]
			# # incx = d_util_meta.strides[1]
			# # _daxpy(&n, &cond_prob, &d_util_meta[dn,0], &incx, &d_util_meta[up,0], &incx)
			for j in range(d_util_meta.shape[1]):
				d_util_meta[up,j] += d_util_meta[dn,j] * cond_prob




cpdef case_dProbability_dFusedParameters(
		int c,

		int n_cases,
		int n_elementals,
		int n_nests,
		int n_edges,
		int n_meta_coef,

		double[:,:] util_elementals,      # shape = [cases,alts]
		double[:,:] util_nests,           # shape = [cases,nests]

		double[:] coef_u_ca,               # shape = (vars_ca)
		double[:,:] coef_u_co,             # shape = (vars_co,alts)
		double[:] coef_q_ca,               # shape = (qvars_ca)
		double[:] coef_mu,                 # shape = (nests)

		double[:,:] d_util_meta,           # shape = (nodes,n_meta_coef)  refs same memory as the d_util_coef_* arrays...
		double[:,:] d_util_coef_u_ca,      # shape = (nodes,vars_ca)
		double[:,:,:] d_util_coef_u_co,    # shape = (nodes,vars_co,alts)
		double[:,:] d_util_coef_q_ca,      # shape = (nodes,qvars_ca)
		double[:,:] d_util_coef_mu,        # shape = (nodes,nests)

		double[:,:] log_conditional_prob,  # shape = (cases,edges)
		double[:,:] total_probability,     # shape = (cases,nodes)

		double[:,:  ] d_prob_meta,         # shape = (nodes,n_meta_coef)  refs same memory as the d_util_coef_* arrays...
		double[:,:  ] d_prob_coef_u_ca,    # shape = (nodes,vars_ca)
		double[:,:,:] d_prob_coef_u_co,    # shape = (nodes,vars_co,alts)
		double[:,:  ] d_prob_coef_q_ca,    # shape = (nodes,qvars_ca)
		double[:,:  ] d_prob_coef_mu,      # shape = (nodes,nests)

		int[:] edge_child_slot,            # shape = (edges)
		int[:] edge_parent_slot,           # shape = (edges)
		int[:] first_visit_to_child,       # shape = (edges)

		# Workspace arrays, not input or output but must be pre-allocated

		double[:] scratch,              # shape = (n_meta_coef,)  refs same memory as the scratch_coef_* arrays...
		double[:] scratch_coef_mu,      # shape = (nests,)

):
	cdef int i,j, e, e_rev
	cdef int dn_slot, up_slot, up_slot_in_nests, dn_slot_in_nests
	cdef double multiplier

	for i in range(d_prob_meta.shape[0]):
		for j in range(d_prob_meta.shape[1]):
			d_prob_meta[i,j] = 0

	for e_rev in range(n_edges):
		e = n_edges-e_rev-1

		dn_slot = edge_child_slot[e]
		up_slot = edge_parent_slot[e]
		up_slot_in_nests = up_slot-n_elementals
		dn_slot_in_nests = dn_slot-n_elementals

		for i in range(n_meta_coef):
			scratch[i] = d_util_meta[dn_slot,i] - d_util_meta[up_slot,i]

		if 0:
			# for competitive edges, adjust phi
			# scratch += X_Phi()[edge] - sum over competes(Alloc[compete]*X_Phi[compete])
			pass # TODO, assume no competitive edges for now
		else:
			# adjust Mu for hierarchical structure, noncompete
			if dn_slot_in_nests < 0:
				if util_elementals[c,dn_slot] != -INFINITY:
					scratch_coef_mu[up_slot_in_nests] += (util_nests[c,up_slot_in_nests] - util_elementals[c,dn_slot]) / coef_mu[up_slot_in_nests]
			else:
				if util_nests[c,dn_slot_in_nests] != -INFINITY:
					scratch_coef_mu[up_slot_in_nests] += (util_nests[c,up_slot_in_nests] - util_nests[c,dn_slot_in_nests]) / coef_mu[up_slot_in_nests]

		multiplier = total_probability[c,up_slot]/coef_mu[up_slot_in_nests]
		for i in range(n_meta_coef):
			scratch[i] *= multiplier
			scratch[i] += d_prob_meta[up_slot, i]
			d_prob_meta[dn_slot, i] += scratch[i] * exp(log_conditional_prob[c,e])

