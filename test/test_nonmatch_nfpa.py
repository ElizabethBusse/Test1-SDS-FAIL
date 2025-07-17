results = {'Health': {'value_html': '3', 'description': 'Can cause serious or permanent injury.'}, 'Flammability': {'value_html': '2', 'description': 'Must be moderately heated or exposed to relatively high ambient temperatures before ignition can occur.'}, 'Instability': {'value_html': '0', 'description': 'Normally stable, even under fire conditions.'}, 'Special': {'value_html': None, 'description': ''}}, {}, {'Health': {'value_html': '4', 'description': 'Can cause serious or permanent injury.'}, 'Flammability': {'value_html': '2', 'description': 'Must be moderately heated or exposed to relatively high ambient temperatures before ignition can occur.'}, 'Instability': {'value_html': '0', 'description': 'Normally stable, even under fire conditions.'}, 'Special': {'value_html': None, 'description': ''}}

def compare_nfpa_results(results):
    # Filter out blank/None results
    filtered = [r for r in results if r and isinstance(r, dict) and r.get('Health')]

    if not filtered:
        return None

    # Compare the filtered results for consensus (ignoring blank)
    first = filtered[0]
    consensus = all(
        r['Health']['value_html'] == first['Health']['value_html'] and
        r['Flammability']['value_html'] == first['Flammability']['value_html'] and
        r['Instability']['value_html'] == first['Instability']['value_html'] and
        r['Special']['value_html'] == first['Special']['value_html']
        for r in filtered
    )

    consensus_result = first if consensus else filtered
    return consensus_result

conn = compare_nfpa_results(results)
print(len(conn))