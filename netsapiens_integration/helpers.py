from typing import Dict, List


def get_callid_tuples_from_subscription_event(events: List[Dict]) -> List[Dict]:
    callid_orig_by_term_pairings_list = []
    for cdr in events:
        netsapiens_orig_callid = cdr.get("orig_callid")
        netsapiens_by_callid = cdr.get("by_callid")
        netsapiens_term_callid = cdr.get("term_callid")
        callid_orig_by_term_pairings_list.append(
            {"orig_callid": netsapiens_orig_callid, "by_callid": netsapiens_by_callid, "term_callid": netsapiens_term_callid}
        )
    return callid_orig_by_term_pairings_list
