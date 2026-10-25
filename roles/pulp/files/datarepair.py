from logging import getLogger

from django.db import transaction

from pulpcore.app import models
from pulpcore.app.models import ProgressReport
from pulpcore.app.util import get_domain

log = getLogger(__name__)


def repair_7272(dry_run=False):
    """
    Repair repository version content_ids cache and content count mismatches (Issue #7272).

    This task fixes two types of data corruption within the current domain:
    1. Mismatch between RepositoryVersion.content_ids cache and actual RepositoryContent
       relationships
    2. Mismatch between RepositoryVersionContentDetails count and actual RepositoryContent count

    Args:
        dry_run (bool): If True, only report issues without fixing them. Defaults to False.
    """
    number_broken = 0

    domain = get_domain()

    log.info(f'Performing datarepair for issue #7272 for domain "{domain.name}"')

    repos = models.Repository.objects.filter(pulp_domain=domain)
    total_versions = models.RepositoryVersion.objects.filter(repository__in=repos).count()

    with (
        ProgressReport(
            message="Repositories checked",
            code="repair.7272.repos_checked",
            total=repos.count(),
        ) as repos_progress,
        ProgressReport(
            message="Repository versions checked",
            code="repair.7272.versions_checked",
            total=total_versions,
        ) as versions_progress,
        ProgressReport(
            message="Repository versions fixed",
            code="repair.7272.versions_fixed",
        ) as fixed_progress,
    ):
        for repo in repos:
            # Fetch only the version PKs up front (small, no content_ids arrays) and load
            # one full version at a time, so at most a single version's content_ids array
            # lives in memory rather than every version's array at once.
            version_ids = list(
                models.RepositoryVersion.objects.filter(repository=repo).values_list(
                    "pk", flat=True
                )
            )
            for rv_id in version_ids:
                rv = models.RepositoryVersion.objects.get(pk=rv_id)
                needs_fix = False
                versions_progress.increment()

                relationships = rv._content_relationships()
                repositorycontent_id_count = relationships.count()

                if rv.content_ids is not None:
                    cache_mismatch = False
                    # Cheap size check first; only fall back to an element comparison when
                    # the counts match, and stream the relationship ids so we never hold a
                    # second full id set in memory alongside the cached one.
                    if len(rv.content_ids) != repositorycontent_id_count:
                        cache_mismatch = True
                    else:
                        cached_id_set = set(rv.content_ids)
                        for content_id in relationships.values_list(
                            "content_id", flat=True
                        ).iterator():
                            if content_id not in cached_id_set:
                                cache_mismatch = True
                                break
                        del cached_id_set
                    if cache_mismatch:
                        log.warning(
                            f'Repository "{repo.name}" (type "{repo.pulp_type}") version '
                            f'{rv.number} in domain "{domain.name}" has a mismatch between the '
                            "RepositoryContent and the cached ID set"
                        )
                        needs_fix = True

                if repositorycontent_id_count == 0:
                    continue
                rv_count_details = models.RepositoryVersionContentDetails.objects.filter(
                    repository_version=rv,
                    count_type=models.RepositoryVersionContentDetails.PRESENT,
                )

                # need to sum across all content types
                total_count = sum(rvcd.count for rvcd in rv_count_details)

                if total_count != repositorycontent_id_count:
                    log.warning(
                        f'Repository "{repo.name}" (type "{repo.pulp_type}") version {rv.number} '
                        f'in domain "{domain.name}" has a mismatch between the RepositoryContent '
                        "and RepositoryVersionContentDetails"
                    )
                    needs_fix = True

                if needs_fix:
                    number_broken += 1

                    if not dry_run:
                        with transaction.atomic():
                            rv.content_ids = list(
                                relationships.values_list("content_id", flat=True).iterator()
                            )
                            rv.save()
                            rv._compute_counts()
                            fixed_progress.increment()

            repos_progress.increment()

        fixed_progress.total = number_broken

    if not number_broken:
        log.info(f'Data repair operation for issue #7272 for domain "{domain.name}" finished. (OK)')
    else:
        if dry_run:
            log.info(
                f"Data repair operation for issue #7272 dry run finished. ({number_broken} "
                f'repository versions need fixing in domain "{domain.name}")'
            )
        else:
            log.info(
                f"Data repair operation for issue #7272 finished. ({number_broken} "
                f'repository versions fixed in domain "{domain.name}")'
            )


def repair_7465(dry_run=False):
    """
    Populates the content_ids cache for all repository versions.
    """
    number_missing = 0
    domain = get_domain()

    log.info(f'Performing datarepair for issue #7465 for domain "{domain.name}"')

    repos = models.Repository.objects.filter(pulp_domain=domain)
    total_versions = models.RepositoryVersion.objects.filter(repository__in=repos).count()

    with (
        ProgressReport(
            message="Repositories checked",
            code="repair.7465.repos_checked",
            total=repos.count(),
        ) as repos_progress,
        ProgressReport(
            message="Repository versions checked",
            code="repair.7465.versions_checked",
            total=total_versions,
        ) as versions_progress,
        ProgressReport(
            message="Repository versions fixed",
            code="repair.7465.versions_fixed",
        ) as fixed_progress,
    ):
        for repo in repos:
            repo_versions = models.RepositoryVersion.objects.filter(repository=repo)
            # All versions count as "checked", but we only need to load the ones whose
            # cache is missing. Filtering on content_ids__isnull avoids pulling the large
            # content_ids arrays for the (already-populated) majority of versions.
            versions_progress.increase_by(repo_versions.count())
            null_version_ids = list(
                repo_versions.filter(content_ids__isnull=True).values_list("pk", flat=True)
            )
            for rv_id in null_version_ids:
                rv = models.RepositoryVersion.objects.get(pk=rv_id)
                number_missing += 1
                if not dry_run:
                    rv.content_ids = list(
                        rv._content_relationships().values_list("content_id", flat=True).iterator()
                    )
                    rv.save()
                    fixed_progress.increment()
            repos_progress.increment()

        fixed_progress.total = number_missing

    if not number_missing:
        log.info(f'Data repair operation for issue #7465 for domain "{domain.name}" finished. (OK)')
    else:
        if dry_run:
            log.info(
                f"Data repair operation for issue #7465 dry run finished. ({number_missing} "
                f'repository versions need fixing in domain "{domain.name}")'
            )
        else:
            log.info(
                f"Data repair operation for issue #7465 finished. ({number_missing} "
                f'repository versions fixed in domain "{domain.name}")'
            )
