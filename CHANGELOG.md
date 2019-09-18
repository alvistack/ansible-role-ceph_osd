# Ansible Role for ceph-osd

## 3.4.0 - TBC

### Major Changes

  - Run molecule test manually on Travis CI

## 3.3.0 - 2019-08-27

### Major Changes

  - Update for RHEL 7
  - Add Vagrant test for RHEL 7
  - Restart service serially

## 3.2.0 - 2019-07-08

### Major Changes

  - Update LXD test profile for Kubernetes v1.15.0 support
  - Fix molecule `group_vars` with links
  - Replace `with_items` with `loop`
  - Replace `with_dict` with `var`
  - Replace `with_first_found` with `lookup('first_found')`
  - Update Vagrant test with `private_network`
  - Reduce default `osd memory target` for better all-in-one support

## 3.1.0 - 2019-06-13

### Major Changes

  - Always include default variables from `vars/main.yml`
  - Always use `become: true` with molecule, especially for vagrant
  - Better multinode test cases

## 3.0.0 - 2019-05-28

  - Initial release for Ansible 2.8 or higher
  - Support both Ubuntu 16.04/18.04 or RHEL/CentOS 7 or openSUSE Leap 15
