# pylint: disable=missing-docstring

import re
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase


class LookupModule(LookupBase):
    # pylint: disable=too-many-branches,too-many-statements

    def run(self, terms, variables=None, regions_enabled=True, **kwargs):
        if 'openshift' not in variables:
            raise AnsibleError("This lookup module requires openshift_facts to be run prior to use")
        if 'master' not in variables['openshift']:
            raise AnsibleError("This lookup module is meant to be run against an OpenShift master host only")

        if 'openshift_master_scheduler_predicates' in variables:
            return variables['openshift_master_scheduler_predicates']
        elif 'scheduler_predicates' in variables['openshift']['master']:
            return variables['openshift']['master']['scheduler_predicates']
        else:
            predicates = []

            if 'deployment_type' not in variables['openshift']['common']:
                raise AnsibleError("This lookup module requires that the deployment_type be set")

            deployment_type = variables['openshift']['common']['deployment_type']

            if 'short_version' in variables['openshift']['common']:
                short_version = variables['openshift']['common']['short_version']
            elif 'openshift_release' in variables:
                release = variables['openshift_release']
                if release.startswith('v'):
                    short_version = release[1:]
                else:
                    short_version = release
            elif 'openshift_version' in variables:
                version = variables['openshift_version']
                short_version = '.'.join(version.split('.')[0:2])
            else:
                # pylint: disable=line-too-long
                raise AnsibleError("Either OpenShift needs to be installed or openshift_release needs to be specified")
            if deployment_type not in ['origin', 'openshift-enterprise']:
                raise AnsibleError("Unknown deployment_type %s" % deployment_type)

            if deployment_type == 'origin':
                if short_version not in ['1.1', '1.2', '1.3', '1.4']:
                    raise AnsibleError("Unknown short_version %s" % short_version)
            elif deployment_type == 'openshift_enterprise':
                if short_version not in ['3.1', '3.2', '3.3', '3.4']:
                    raise AnsibleError("Unknown short_version %s" % short_version)

            if deployment_type == 'openshift-enterprise':
                # convert short_version to origin short_version
                short_version = re.sub('^3.', '1.', short_version)

            if short_version in ['1.1', '1.2']:
                predicates.append({'name': 'PodFitsHostPorts'})
                predicates.append({'name': 'PodFitsResources'})

            # applies to all known versions
            predicates.append({'name': 'NoDiskConflict'})

            # only 1.1 didn't include NoVolumeZoneConflict
            if short_version != '1.1':
                predicates.append({'name': 'NoVolumeZoneConflict'})

            if short_version in ['1.1', '1.2']:
                predicates.append({'name': 'MatchNodeSelector'})
                predicates.append({'name': 'Hostname'})

            if short_version != '1.1':
                predicates.append({'name': 'MaxEBSVolumeCount'})
                predicates.append({'name': 'MaxGCEPDVolumeCount'})

            if short_version not in ['1.1', '1.2']:
                predicates.append({'name': 'GeneralPredicates'})
                predicates.append({'name': 'PodToleratesNodeTaints'})
                predicates.append({'name': 'CheckNodeMemoryPressure'})

            if short_version not in ['1.1', '1.2', '1.3']:
                predicates.append({'name': 'CheckNodeDiskPressure'})
                predicates.append({'name': 'MatchInterPodAffinity'})

            if regions_enabled:
                region_predicate = {
                    'name': 'Region',
                    'argument': {
                        'serviceAffinity': {
                            'labels': ['region']
                        }
                    }
                }
                predicates.append(region_predicate)

            return predicates
