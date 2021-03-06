#!/usr/bin/env python3

# usage:
# python3 comppi_data_overlap.py

#from matplotlib_venn import venn3
import networkx as nx
import itertools
import matplotlib.pyplot as plt
from export_downloads import ComppiInterface

# filter to species: -1: disabled, 0 (human), 1 (drosi), 2 (c.elegans), 3 (yeast)
species_filter = [-1, 0, 1, 2, 3]

# group of custom sources, currently set to protein-protein interaction databases
custom_source_group = ['MINT', 'IntAct', 'MIPS', 'DroID', 'MatrixDB', 'BioGRID', 'HPRD', 'DIP', 'CCSB']
# all proteins from ANY source DB (not intersection, but union!!)
# SELECT COUNT(DISTINCT id) FROM Protein WHERE id IN ( SELECT proteinId FROM ProteinToDatabase WHERE sourceDb IN ('MINT', 'IntAct', 'MIPS', 'MatrixDB', 'DroID', 'BioGRID', 'HPRD', 'HomoMINT', 'DIP', 'CCSB') );

c = ComppiInterface()

for spfilter in species_filter:
	comppi_graph = c.buildGlobalComppi()
	
	with open("comppi_data_overlap_log_sp_{}.txt".format(spfilter), "w") as logfp:
	
		# filter to species if needed
		if spfilter >= 0:
			print("Filtering to species: {}".format(spfilter), file=logfp)
			comppi_graph = c.filterGraph(comppi_graph, None, spfilter)
		
		comppi_number_of_all_nodes = comppi_graph.number_of_nodes()
		print("Number of all nodes: {}".format(comppi_number_of_all_nodes), file=logfp)
		print("\n", file=logfp)
		
		# collect the proteins per source databases and localizations per source databases
		loc_sources = {
			'No Loc Source': []
		}
		prot_sources = {
			'No Protein Source': []
		}
		node_db_mapping = c.getNodeSourceDbs()
		
		for n, d in comppi_graph.nodes_iter(data=True):
			# nodes
			curr_node_dbs = node_db_mapping.get(n)
			if curr_node_dbs is None:
				prot_sources['No Protein Source'].append(n)
			else:
				for sdb in curr_node_dbs:
					prot_sources.setdefault(sdb, [])
					prot_sources[sdb].append(n)
			
			# localizations
			curr_loc_srcs = d.get('loc_source_dbs')
			
			if curr_loc_srcs is None:
				loc_sources['No Loc Source'].append(n)
			else:
				for sdb in curr_loc_srcs:
					nodes_in_curr_src = loc_sources.setdefault(sdb, [])
					nodes_in_curr_src.append(n)
		
		# PROTEINS
		print("---------- PROTEINS ----------", file=logfp)
		print("Number of unique nodes per source database:", file=logfp)
		prot_source_nums = {}
		for src_name, nodes_in_src in prot_sources.items():
			prot_sources[src_name] = set(nodes_in_src)
			prot_source_nums[src_name] = len(prot_sources[src_name])
			print("{}: {}".format(src_name, prot_source_nums[src_name]), file=logfp)
		
		print("\n", file=logfp)
		
		
		print("Number of overlapping nodes for pairwise protein source combinations:", file=logfp)
		node_src_overlaps = nx.Graph()
		for src_db1, src_db2 in itertools.combinations(prot_source_nums.keys(), 2):
			common_nodes = set.intersection(prot_sources[src_db1], prot_sources[src_db2])
			common_nodes_len = len(common_nodes)
			print("{} ∩ {}: {}".format(src_db1, src_db2, common_nodes_len), file=logfp)
			
			node_src_overlaps.add_node(
				src_db1,
				{
					'label': "{} ({})".format(src_db1, prot_source_nums[src_db1]),
					'num_of_nodes': prot_source_nums[src_db1]
				}
			)
			node_src_overlaps.add_node(
				src_db2,
				{
					'label': "{} ({})".format(src_db2, prot_source_nums[src_db2]),
					'num_of_nodes': prot_source_nums[src_db2]
				}
			)
			if common_nodes_len:
				node_src_overlaps.add_edge(src_db1, src_db2, {'weight': common_nodes_len})
		
		
		# common proteins in all source databases
		all_prot_sets = []
		all_prot_sets_5k = [] # source DBs with more than 5'000 proteins
		all_prot_sets_custom = []
		all_prot_dbs = []
		for db_name, node_id_set in prot_sources.items():
			if db_name != 'No Protein Source':
				all_prot_dbs.append(db_name)
				all_prot_sets.append(node_id_set)
				
				if prot_source_nums[db_name] > 5000:
					all_prot_sets_5k.append(node_id_set)
				
				if db_name in custom_source_group:
					all_prot_sets_custom.append(node_id_set)
				
		all_common_prots = set.intersection(*all_prot_sets)
		all_common_prots_len = len(all_common_prots)
		print("\nCommon proteins in all source databases: {}\n(Sources: {})".format(
			all_common_prots_len,
			','.join(all_prot_dbs)
		), file=logfp)
		
		all_common_prots_5k = set.intersection(*all_prot_sets_5k)
		all_common_prots_len_5k = len(all_common_prots_5k)
		print("\nCommon proteins in all source databases with at least 5'000 proteins: {}\n(Sources: {})".format(
			all_common_prots_len_5k,
			','.join(all_prot_dbs)
		), file=logfp)
		
		all_common_prots_custom = set.intersection(*all_prot_sets_custom)
		all_common_prots_len_custom = len(all_common_prots_custom)
		print("\nCommon proteins in all PPI source databases: {}\n(Sources: {})".format(
			all_common_prots_len_custom,
			','.join(custom_source_group)
		), file=logfp)
		if all_common_prots_len_custom < 100:
			print("These protein IDs are: ", file=logfp)
			print(all_common_prots_custom, file=logfp)
		
		
		# export
		print("\n", file=logfp)
		#print("Exporting the protein sources overlap graph...")
		
		nx.write_gml(node_src_overlaps, "comppi_protein_source_overlap_sp_{}.gml".format(spfilter))
		
		
		# LOCALIZATIONS
		print("---------- LOCALIZATIONS ----------", file=logfp)
		# number of protein-localization associations per each source database
		print("Number of unique node-localization associations per source:", file=logfp)
		loc_source_nums = {}
		for src_name, nodes_in_src in loc_sources.items():
			loc_sources[src_name] = set(nodes_in_src)
			loc_source_nums[src_name] = len(loc_sources[src_name])
			print("{}: {}".format(src_name, loc_source_nums[src_name]), file=logfp)
		
		print("\n", file=logfp)
		
		
		print("Number of overlapping nodes for pairwise localization source combinations:", file=logfp)
		loc_src_overlaps = nx.Graph()
		for src_db1, src_db2 in itertools.combinations(loc_source_nums.keys(), 2):
			common_nodes = set.intersection(loc_sources[src_db1], loc_sources[src_db2])
			common_nodes_len = len(common_nodes)
			print("{} ∩ {}: {}".format(src_db1, src_db2, common_nodes_len), file=logfp)
			
			loc_src_overlaps.add_node(
				src_db1,
				{
					'label': "{} ({})".format(src_db1, loc_source_nums[src_db1]),
					'num_of_nodes': loc_source_nums[src_db1]
				}
			)
			loc_src_overlaps.add_node(
				src_db2,
				{
					'label': "{} ({})".format(src_db2, loc_source_nums[src_db2]),
					'num_of_nodes': loc_source_nums[src_db2]
				}
			)
			if common_nodes_len:
				loc_src_overlaps.add_edge(src_db1, src_db2, {'weight': common_nodes_len})
		
		# export
		print("", file=logfp)
		#print("Exporting the localization sources overlap graph...")
		
		nx.write_gml(loc_src_overlaps, "comppi_loc_source_overlap_sp_{}.gml".format(spfilter))
	
	# visualize
	#nx.draw_networkx(
	#	source_overlaps,
	#	pos=nx.spring_layout(source_overlaps),
	#	label = 'Pairwise overlap between the ComPPI source databases',
	#	with_labels = True,
	#	labels = ["{}\n({})".format(n, attr['num_of_nodes']) for n, attr in source_overlaps.nodes_iter(data=True)],
	#	node_size = [attr['weight']*100 for _, __, attr in source_overlaps.edges_iter(data=True)],
	#	node_color = '#ffffff',
	#	edge_color = '#909090',
	#	width = 
	#)
	#
	#plt.axis('off')
	#plt.savefig("comppi_data_overlap.png")
	
	# overlaps on figure
	Y = list(prot_source_nums.values())
	Y.append(all_common_prots_len)
	Y.append(comppi_number_of_all_nodes)
	
	X = [i for i in range( (len(prot_source_nums) + 2) )] # +2: common, comppi
	X_labels = list(prot_source_nums.keys())
	X_labels.append('Common In All')
	X_labels.append('ComPPI')
	X_labels = tuple(X_labels)
	
	fig, axes = plt.subplots(figsize=(10,12), dpi=300)
	plt.grid(True)
	axes.set_title('Number of Proteins Per Source')
	
	#axes.set_xlabel('Source Databases')
	#plt.xticks(X, X_labels)
	
	axes.set_xticks(X)
	axes.set_xticklabels(X_labels, rotation=45)
	
	#axes.set_xticklabels( X_labels )
	#axes.get_xaxis().set_ticks([])
	
	#axes.get_xaxis().set_visible(False)
	axes.set_ylabel('Number of Proteins')
	axes.tick_params(axis='both', which='major', labelsize=10)
	axes.tick_params(axis='both', which='minor', labelsize=8)
	axes.bar(X, Y, align='center', color='#F2AE6E', edgecolor='#ffffff', alpha=1, linewidth=1)
	fig.savefig('number_of_proteins_per_source_sp_{}.png'.format(spfilter))
	
	
	del comppi_graph;